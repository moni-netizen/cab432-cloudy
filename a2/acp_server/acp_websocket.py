from __future__ import annotations

import argparse
import asyncio
import itertools
import logging
import sys
from contextlib import suppress
from pathlib import Path

import base64
import time
import uuid
from decimal import Decimal

import boto3
import json

from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

HOST = "127.0.0.1"
PORT = 7331
PATH = "/acp"
AGENT_SCRIPT = Path(__file__).parents[1] / "bedrock_gemma" / "test_llm.py"
AGENT_PYTHON = Path(__file__).parents[1] / "bedrock_gemma" / "venv" / "Scripts" / "python.exe"  # Windows
LOGGER = logging.getLogger(__name__)
CONNECTION_IDS = itertools.count(1)

DDB_TABLE = "n12023868-message-history"
S3_BUCKET = "n12023868-images-history"
REGION = "ap-southeast-2"



dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DDB_TABLE)
s3 = boto3.client("s3", region_name=REGION)

def _extract_message_text(parsed: dict) -> tuple[str, str] | None:
    """Return (kind, text) for a prompt or an agent response chunk, else None."""
    method = parsed.get("method")

    if method == "session/prompt":
        prompt_blocks = parsed.get("params", {}).get("prompt", [])
        texts = [block.get("text", "") for block in prompt_blocks if block.get("type") == "text"]
        return ("prompt", "\n".join(texts)) if texts else None

    if method == "session/update":
        update = parsed.get("params", {}).get("update", {})
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content", {})
            if content.get("type") == "text":
                text = content.get("text", "")
                return ("response_chunk", text) if text else None

    return None

def _extract_images(obj, message_id: str, images: list) -> None:
    """Recursively find image content blocks, collect their bytes for S3,
    and replace the base64 payload in place with a reference."""
    if isinstance(obj, dict):
        if obj.get("type") == "image" and "data" in obj:
            key = f"{message_id}/{uuid.uuid4()}.bin"
            image_bytes = base64.b64decode(obj["data"])
            images.append((key, image_bytes, obj.get("mimeType", "application/octet-stream")))
            obj["data"] = f"s3://{S3_BUCKET}/{key}"
        else:
            for value in obj.values():
                _extract_images(value, message_id, images)
    elif isinstance(obj, list):
        for item in obj:
            _extract_images(item, message_id, images)

def _store_message_sync(connection_id: int, direction: str, raw_message: str) -> None:
    try:
        parsed = json.loads(raw_message)
    except json.JSONDecodeError:
        return  # not JSON, nothing to store

    prompt_text = _extract_message_text(parsed)

    if prompt_text is None:
        return  # not a prompt message, skip storing entirely

    kind, text = prompt_text

    message_id = str(uuid.uuid4())
    images: list = []
    _extract_images(parsed, message_id, images)

    for key, image_bytes, content_type in images:
        s3.put_object(Bucket=S3_BUCKET, Key=key, Body=image_bytes, ContentType=content_type)

    table.put_item(Item={
        "connectionId": connection_id,
        "messageId": message_id,
        "direction": direction,
        "kind": kind,  # "prompt" or "response_chunk"
        "timestamp": Decimal(str(time.time())),
        "prompt": text,
        "imageKeys": [key for key, _, _ in images],
    })

async def record_message(connection_id: int, direction: str, raw_message: str) -> None:
    try:
        await asyncio.to_thread(_store_message_sync, connection_id, direction, raw_message)
    except Exception:
        LOGGER.exception(
            "Connection %s: failed to persist %s message", connection_id, direction
        )


async def relay(websocket: ServerConnection) -> None:
    """Run one stdio ACP agent and relay this browser connection to it."""
    if websocket.request.path != PATH:
        LOGGER.warning("Rejected WebSocket connection to %s", websocket.request.path)
        await websocket.close(code=1008, reason="Use the /acp WebSocket endpoint")
        return

    connection_id = next(CONNECTION_IDS)
    try:
        process = await asyncio.create_subprocess_exec(
            str(AGENT_PYTHON),
            "-u",
            str(AGENT_SCRIPT),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=AGENT_SCRIPT.parent,
        )
    except OSError:
        LOGGER.exception("Connection %s: could not start the ACP agent", connection_id)
        await websocket.close(code=1011, reason="Could not start the ACP agent; check the server log")
        return

    LOGGER.info("Connection %s: started ACP agent process %s", connection_id, process.pid)
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None

    storage_tasks: set[asyncio.Task] = set()
    browser_to_agent = asyncio.create_task(copy_to_agent(connection_id, websocket, process.stdin, storage_tasks))
    agent_to_browser = asyncio.create_task(copy_to_browser(connection_id, process.stdout, websocket, storage_tasks))
    log_stderr = asyncio.create_task(log_agent_stderr(process.stderr, connection_id))

    try:
        done, pending = await asyncio.wait(
            (browser_to_agent, agent_to_browser),
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task.result()
        if agent_to_browser in done and websocket.close_code is None:
            # EOF on stdout means that the child stopped without closing the
            # browser transport itself. Wait briefly so its exit status and
            # final stderr lines are available in the diagnostic below.
            with suppress(TimeoutError):
                await asyncio.wait_for(process.wait(), timeout=1)
            LOGGER.error(
                "Connection %s: ACP agent closed stdout unexpectedly (exit status %s)",
                connection_id,
                process.returncode if process.returncode is not None else "not yet available",
            )
            await websocket.close(
                code=1011,
                reason="ACP agent stopped unexpectedly; check the server log",
            )
    except ValueError as error:
        LOGGER.warning("Connection %s: invalid WebSocket message: %s", connection_id, error)
        await websocket.close(code=1003, reason=str(error))
    except ConnectionClosed:
        pass
    except Exception:
        LOGGER.exception("Connection %s: ACP relay failed", connection_id)
        with suppress(ConnectionClosed):
            await websocket.close(code=1011, reason="ACP relay failed; check the server log")
    finally:
        await stop_agent(process)
        # Let the stderr reader drain messages written while the process was
        # shutting down instead of cancelling it before the useful error.
        with suppress(TimeoutError):
            await asyncio.wait_for(log_stderr, timeout=1)
        if not log_stderr.done():
            log_stderr.cancel()
            await asyncio.gather(log_stderr, return_exceptions=True)
        LOGGER.info(
            "Connection %s: ACP agent process %s stopped with exit status %s",
            connection_id,
            process.pid,
            process.returncode,
        )
#endregion websocket-relay


#region relay-records
async def copy_to_agent(connection_id: int, websocket: ServerConnection, stdin: asyncio.StreamWriter, storage_tasks: set[asyncio.Task]) -> None:
    async for message in websocket:
        if isinstance(message, bytes) or "\n" in message or "\r" in message:
            raise ValueError("ACP WebSocket messages must be one text JSON-RPC record")
        task = asyncio.create_task(record_message(connection_id, "to_agent", message))
        storage_tasks.add(task)
        task.add_done_callback(storage_tasks.discard)
        stdin.write(message.encode("utf-8") + b"\n")
        await stdin.drain()


async def copy_to_browser(connection_id: int, stdout: asyncio.StreamReader, websocket: ServerConnection, storage_tasks: set[asyncio.Task]) -> None:
    while line := await stdout.readline():
        message = line.rstrip(b"\r\n")
        if message:
            text = message.decode("utf-8")
            task = asyncio.create_task(record_message(connection_id, "to_browser", text))
            storage_tasks.add(task)
            task.add_done_callback(storage_tasks.discard)
            await websocket.send(text)
#endregion relay-records


async def log_agent_stderr(stderr: asyncio.StreamReader, connection_id: int) -> None:
    while line := await stderr.readline():
        LOGGER.warning(
            "Connection %s, ACP agent stderr: %s",
            connection_id,
            line.decode(errors="replace").rstrip(),
        )


async def stop_agent(process: asyncio.subprocess.Process) -> None:
    if process.stdin is not None:
        process.stdin.close()
        with suppress(BrokenPipeError, ConnectionResetError):
            await process.stdin.wait_closed()
    with suppress(TimeoutError):
        await asyncio.wait_for(process.wait(), timeout=2)
        return
    process.terminate()
    with suppress(TimeoutError):
        await asyncio.wait_for(process.wait(), timeout=2)
        return
    process.kill()
    await process.wait()


#region websocket-server
async def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the CAB432 ACP agent over WebSocket.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", default=PORT, type=int)
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="log connections and child-process lifecycle details",
    )
    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.INFO)
    async with serve(relay, args.host, args.port):
        print(f"ACP server listening at ws://{args.host}:{args.port}{PATH}")
        await asyncio.Future()
#endregion websocket-server


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
