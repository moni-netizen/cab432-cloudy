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
        "You are a manager tasked with triaging issues and pull requests for the Github Repo."
        "Help users manage this repository, be ready to communicate clearly and respond when they say hello."
        "use process_pull_request to process pull requests by id."
        "use check_and_store to find the three most similar issues to an issue, and store this to the s3 vectors. the return object will be used to write an appropriate comment to this new issue."
        "use write_comment to write a comment to an issue."
        "please be nice to the chatter. if you require more clarification about your tasks, you must ask for more clarification."
        # "If a user gives you a prompt about a pull request or issue, please use process_pull_request to summarise it, provide the user who filed a pull request and its current state."
        # "To comment on an issue, use check_and_store to find similar issues and store new ones in S3, then call write_comment to write to the repo. "
    ),
    toolsets=[mcp_toolset],
)



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
    run_acp_stdio_sync(agent, name = "CAB432 A2 TEST MCP AGENT", version = "1.0.0")
    #asyncio.run(chat())
