"""This is so i don't forget!
    12/09 -> summarise a PR and describe its purpose, priority and status.
    13/09 -> add image support (on bedrock 13/09)
    14/09 -> connected ACP to gemma to MCP! yay!
    15/09 -> added s3vector support for comments
    16/09 -> completed (hopefully) all the scenarios locally
             
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import asyncio

from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.bedrock import BedrockConverseModel
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.providers.bedrock import BedrockProvider
from pydantic_ai_harness.experimental import HarnessExperimentalWarning

# get rid of that dumb dumb logo
warnings.filterwarnings("ignore", category=HarnessExperimentalWarning)
from pydantic_ai_harness.experimental.acp import run_acp_stdio_sync


REGION = os.getenv("AWS_REGION", "ap-southeast-2")
MODEL_ID = "nvidia.nemotron-super-3-120b"

# for now, this is my git access file :(
# change later to the actual MCP server in the cloud
MCP_SERVER = Path(__file__).parents[1] / "mcp_server" / "github_access.py"
MCP_VENV_PYTHON = Path(__file__).parents[1] / "mcp_server" / "venv" / "Scripts" / "python.exe"  # Windows

model = BedrockConverseModel(MODEL_ID, provider=BedrockProvider(region_name=REGION))
mcp_toolset = MCPToolset(StdioTransport(command=str(MCP_VENV_PYTHON), args=[str(MCP_SERVER)]))

agent = Agent(
    model,
    instructions=(
        "You are a manager tasked with triaging issues and pull requests for the Github Repo. "
        "Use the celsius to fahrenheit tool to convert between celsius and fahrenheit"
        # "If a user gives you a prompt about a pull request or issue, please use process_pull_request to summarise it, provide the user who filed a pull request and its current state."
        # "To comment on an issue, use check_and_store to find similar issues and store new ones in S3, then call write_comment to write to the repo. "
    ),
    toolsets=[mcp_toolset],
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
def parse_input(raw: str) -> tuple[str, Path | None]:
    """Pulls out a file path token that resolves to a real image, leaving the rest as prompt text."""
    tokens = raw.split()
    image_path = None
    remaining = []

    for token in tokens:
        candidate = Path(token)
        if image_path is None and candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTENSIONS:
            image_path = candidate
        else:
            remaining.append(token)

    return " ".join(remaining).strip(), image_path


# async def chat() -> None:
#     """Keep one MCP connection and one conversation history for the chat session."""
#     message_history = None
#     print("Ask a question, or type 'quit' to exit.")
#     print("Try: Summarise Pull Request 707.")

#     # Entering the agent starts the MCP stdio server and discovers its tools.
#     async with agent:
#         while True:
#             raw = input("You: ").strip()
#             if raw.lower() in {"quit", "exit"}:
#                 break
#             if not raw:
#                 continue

#             prompt_text, image_path = parse_input(raw)
#             content: list = []
#             if prompt_text:
#                 content.append(prompt_text)
#             if image_path:
#                 media_type = mimetypes.guess_type(str(image_path))[0] or "image/png"
#                 content.append(BinaryContent(data=image_path.read_bytes(), media_type = media_type))
            
#             if not content:
#                 continue

#             # Include earlier messages so the agent can follow the conversation.
#             result = await agent.run(content, message_history=message_history)
#             message_history = result.all_messages()
#             print(f"Assistant: {result.output}")

async def chat() -> None:
    """Keep one MCP connection and one conversation history for the chat session."""
    message_history = None
    print("Ask a question, or type 'quit' to exit.")
    print("Try: Convert 20 degrees Celsius to Fahrenheit.")

    # Entering the agent starts the MCP stdio server and discovers its tools.
    async with agent:
        while True:
            prompt = input("You: ").strip()
            if prompt.lower() in {"quit", "exit"}:
                break
            if not prompt:
                continue

            # Include earlier messages so the agent can follow the conversation.
            result = await agent.run(prompt, message_history=message_history)
            message_history = result.all_messages()
            print(f"Assistant: {result.output}")


if __name__ == "__main__":
    #run_acp_stdio_sync(agent, name = "CAB432 A2 TEST MCP AGENT", version = "1.0.0")
    asyncio.run(chat())
