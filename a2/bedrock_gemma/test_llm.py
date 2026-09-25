"""This is so i don't forget!
    12/09 -> summarise a PR and describe its purpose, priority and status.
    13/09 -> add image support (on bedrock 13/09)
    14/09 -> connected ACP to gemma to MCP! yay!
    15/09 -> added s3vector support for comments
    16/09 -> completed (hopefully) all the scenarios locally
    17/09 -> got process_pull_request (my first tool) again after breaking my stuff
    18/09 -> the trio are together! sorta...
    19/09 -> configured dynamodb message history
    20/09 -> got s3 working sorta, gemma is so stupid
    21/09 -> implemented two models and now works locally!!!!!!

    time taken: 9 days...
             
"""

# holy imports bro
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import argparse
import asyncio
from aiohttp import web

from fastmcp.client.transports import StreamableHttpTransport
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai_harness.experimental import HarnessExperimentalWarning

import dataclasses
from pydantic_ai.capabilities.hooks import Hooks
from pydantic_ai.messages import ModelRequest, UserPromptPart, BinaryContent
from pydantic_ai.models import ModelRequestContext
from pydantic_ai import RunContext

# get rid of that dumb dumb logo
warnings.filterwarnings("ignore", category=HarnessExperimentalWarning)
from pydantic_ai_harness.experimental.acp import run_acp_stdio_sync
from fastmcp.client.transports import StreamableHttpTransport

import boto3
import json

# aws secrets function
# i prolly shoulda used parameter store for most of this but alas
def get_secret() -> dict:

    secret_name = "n12023868-secrets"
    region_name = "ap-southeast-2"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    return json.loads(response['SecretString'])

secrets = get_secret()

# an added layer of security i guess, can only access tools if we have the right token
# which i set to a funny password
MCP_SHARED_TOKEN = secrets["MCP_SHARED_TOKEN"]

REGION = os.getenv("AWS_REGION", "ap-southeast-2")
VISION_MODEL_ID = "google.gemma-3-12b-it"
vision_model = BedrockConverseModel(VISION_MODEL_ID, provider=BedrockProvider(region_name=REGION))

# gemma has eyes, so it should be able to process any images coming in the chat and issues box
# and caption it
caption_agent = Agent(
    vision_model,
    instructions="Describe this image in exactly 1-2 concise, factual sentences. No preamble, no extra commentary.",
)

async def _caption_image(image: BinaryContent) -> str:
    result = await caption_agent.run([image])
    return result.output


async def caption_images_before_request(
    ctx: RunContext[None], request_context: ModelRequestContext
) -> ModelRequestContext:
    """Runs before every call to the main (Nemotron) model. Detects any image
    content in the outgoing messages, replaces it with a short text caption
    from the Gemma vision model, so Nemotron only ever sees text."""
    new_messages = []
    context_changed = False

    for message in request_context.messages:
        if not isinstance(message, ModelRequest):
            new_messages.append(message)
            continue

        new_parts = []
        message_changed = False
        for part in message.parts:
            if isinstance(part, UserPromptPart) and isinstance(part.content, list):
                new_content = []
                for item in part.content:
                    if isinstance(item, BinaryContent) and item.media_type.startswith("image/"):
                        caption = await _caption_image(item)
                        new_content.append(f"[Attached image — description: {caption}]")
                        message_changed = True
                    else:
                        new_content.append(item)
                new_parts.append(dataclasses.replace(part, content=new_content) if message_changed else part)
            else:
                new_parts.append(part)

        if message_changed:
            new_messages.append(dataclasses.replace(message, parts=new_parts))
            context_changed = True
        else:
            new_messages.append(message)

    return dataclasses.replace(request_context, messages=new_messages) if context_changed else request_context


hooks = Hooks(before_model_request=caption_images_before_request)

MODEL_ID = "nvidia.nemotron-super-3-120b"
model = BedrockConverseModel(MODEL_ID, provider=BedrockProvider(region_name=REGION))

MCP_SERVER_URL = secrets["MCP_SERVER_URL"]
mcp_toolset = MCPToolset(StreamableHttpTransport(MCP_SERVER_URL,
auth = MCP_SHARED_TOKEN), init_timeout=30.0)

# nemo, main model but blind as a bat, so thats why they work together
agent = Agent(
    model,
    instructions=(
        "You are a manager tasked with triaging issues and pull requests for the Github Repo."
        "Help users manage this repository, be ready to communicate clearly and respond when they say hello."
        "use process_pull_request to process pull requests by id."
        "use check_and_store to find the three most similar issues to an issue, and store this to the s3 vectors. you are to list the similarities between your issue and the vector results, but do not make a comment, just respond to the chat."
        "please be nice to the chatter. if you require more clarification about your tasks, you must ask for more clarification."
    ),
    toolsets=[mcp_toolset],
    capabilities=[hooks],
)

# configuring my schedule receiver server
TRIGGER_PORT = 8080

async def handle_trigger_comment(request: web.Request) -> web.Response:
    auth_header = request.headers.get("Authorization", "")
    if auth_header != f"Bearer {MCP_SHARED_TOKEN}":
        return web.json_response({"error": "unauthorized"}, status=401)

    try:
        body = await request.json()
        issue_id = body["issue_id"]
    except (ValueError, KeyError):
        return web.json_response({"error": 'expected {"issue_id": <int>}'}, status=400)

    async with agent:
        result = await agent.run(
            f"A new issue #{issue_id} was filed. Find similar issues and write an appropriate comment on it, ensuring you link these three issues for the user to explore."
        )

    return web.json_response({"status": "ok", "issue_id": issue_id, "summary": result.output})

async def run_trigger_server() -> None:
    app = web.Application()
    app.router.add_post("/trigger-comment", handle_trigger_comment)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", TRIGGER_PORT)
    await site.start()
    print(f"Trigger server listening on http://0.0.0.0:{TRIGGER_PORT}/trigger-comment")
    await asyncio.Future()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-trigger", action="store_true")
    args = parser.parse_args()

    if args.serve_trigger:
        asyncio.run(run_trigger_server())
    else:
        run_acp_stdio_sync(agent, name = "CAB432 A2 MCP AGENT", version = "1.0.0")
