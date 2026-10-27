from __future__ import annotations

import argparse
import asyncio
import http
import itertools
import logging
import sys

from contextlib import suppress
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "bedrock_model"))

import base64
import time
import uuid
from decimal import Decimal

import boto3
import json
from botocore.exceptions import ClientError
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

logging.basicConfig(level = logging.INFO)

HOST = "0.0.0.0"
PORT = 3000
PATH = "/acp"
AGENT_SCRIPT = Path(__file__).parents[1] / "bedrock_model" / "chatbot.py"
AGENT_PYTHON = sys.executable

LOGGER = logging.getLogger(__name__)
CONNECTION_IDS = itertools.count(1)

MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_ACP_MESSAGE_BYTES = 32 * 1024 * 1024
SUBPROCESS_LINE_LIMIT = 40 * 1024 * 1024


DDB_TABLE = "n12023868-message-history"
S3_BUCKET = "n12023868-images-history"
REGION = "ap-southeast-2"

dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DDB_TABLE)
s3 = boto3.client("s3", region_name=REGION)

# module-level state — assumes one in-flight session per connection at a time,
# consistent with your current one-subprocess-per-connection architecture
_response_buffers: dict[int, list[str]] = {}
_response_sessions: dict[int, str] = {}

def _extract_prompt(parsed: dict) -> tuple[str, str, list[dict]] | None:
    """Return (text, sessionId, image_blocks) for a session/prompt request."""
    if parsed.get("method") != "session/prompt":
        return None
    params = parsed.get("params", {})
    blocks = params.get("prompt", [])
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    image_blocks = [b for b in blocks if b.get("type") == "image" and "data" in b]
    text = "\n".join(texts)
    if not text and not image_blocks:
        return None
    return (text, params.get("sessionId"), image_blocks)

def _extract_chunk(parsed: dict) -> tuple[str, str] | None:
    """Return (text, sessionId) for one agent_message_chunk update."""
    if parsed.get("method") != "session/update":
        return None
    params = parsed.get("params", {})
    update = params.get("update", {})
    if update.get("sessionUpdate") != "agent_message_chunk":
        return None
    content = update.get("content", {})
    if content.get("type") != "text":
        return None
    text = content.get("text", "")
    return (text, params.get("sessionId")) if text else None


def _extract_final_result(parsed: dict) -> dict | None:
    """Return the result dict if this message is the turn-ending response."""
    result = parsed.get("result")
    if isinstance(result, dict) and "stopReason" in result:
        return result
    return None

def _store_row_sync(connection_id: int, kind: str, text: str, session_id: str | None,
                     stop_reason: str | None = None, usage: dict | None = None,
                     image_blocks: list[dict] | None = None) -> None:
    message_id = str(uuid.uuid4())
    image_keys = []

    for block in (image_blocks or []):
        
        image_bytes = base64.b64decode(block["data"])
        content_type = block.get("mimeType", "application/octet-stream")
        key = f"{message_id}/{uuid.uuid4()}.{content_type.split("/")[1]}"
        response = s3.put_object(Bucket=S3_BUCKET, Key=key, Body=image_bytes, ContentType=content_type)
        if response:
            print(f"response: {response['ResponseMetadata']['HTTPStatusCode']}")
        image_keys.append(key)

    item = {
        "connectionId": connection_id,
        "messageId": message_id,
        "kind": kind,
        "sessionId": session_id,
        "text": text,
        "timestamp": Decimal(str(time.time())),
        "imageKeys": image_keys,
    }
    if stop_reason is not None:
        item["stopReason"] = stop_reason
    if usage:
        item["usage"] = {k: Decimal(str(v)) for k, v in usage.items()}

    table.put_item(Item=item)

async def record_message(connection_id: int, direction: str, raw_message: str) -> None:
    try:
        parsed = json.loads(raw_message)
    except json.JSONDecodeError:
        LOGGER.warning("Connection %s: non-JSON message, len=%d", connection_id, len(raw_message))
        return

    if parsed.get("method") == "session/prompt":
        LOGGER.info("Connection %s: raw session/prompt params = %s", connection_id, parsed.get("params"))

    prompt = _extract_prompt(parsed)
    if prompt is not None:
        text, session_id, image_blocks = prompt
        try:
            await asyncio.to_thread(
                _store_row_sync, connection_id, "prompt", text, session_id,
                image_blocks=image_blocks,
            )
        except Exception:
            LOGGER.exception("Connection %s: failed to persist prompt", connection_id)
        return

    chunk = _extract_chunk(parsed)
    if chunk is not None:
        text, session_id = chunk
        _response_buffers.setdefault(connection_id, []).append(text)
        _response_sessions[connection_id] = session_id
        return

    final = _extract_final_result(parsed)
    if final is not None:
        chunks = _response_buffers.pop(connection_id, [])
        session_id = _response_sessions.pop(connection_id, None)
        if not chunks:
            return  # nothing buffered (e.g. a tool-call result with a stopReason-shaped result you don't expect)
        full_text = "".join(chunks)
        try:
            await asyncio.to_thread(
                _store_row_sync, connection_id, "response", full_text, session_id,
                stop_reason=final.get("stopReason"), usage=final.get("usage"),
            )
        except Exception:
            LOGGER.exception("Connection %s: failed to persist response", connection_id)
        return


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
            limit=SUBPROCESS_LINE_LIMIT,
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

async def health_check_handler(connection, request):
    """
    Intercepts the HTTP handshake. If the path is /health, 
    it returns an HTTP 200 OK immediately without upgrading to WebSockets.
    """
    if request.path == "/health":
        return connection.respond(http.HTTPStatus.OK, "OK\n")
    
    # Returning None tells the library to proceed with the normal WebSocket handshake
    return None

def pick_subprotocol(connection, subprotocols):
    LOGGER.warning("Client offered subprotocols: %s", list(subprotocols))
    return subprotocols[0] if subprotocols else None

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
    async with serve(
        relay,
        args.host,
        args.port,
        select_subprotocol=pick_subprotocol,
        process_request = health_check_handler,
        max_size=MAX_ACP_MESSAGE_BYTES,
        max_queue=8,
        compression=None,
    ):
        print(f"ACP server listening at ws://{args.host}:{args.port}{PATH}")
        await asyncio.Future()
#endregion websocket-server


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s", stream=sys.stderr)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
