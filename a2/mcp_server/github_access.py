from __future__ import annotations
# this is meant to hold the MCP server (for now) and define my toolkit
from github import Auth, Github
from fastmcp import FastMCP
#import boto3
#import json

# my super scummy PAT storage (sorry)
token = "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"

#github stuff
auth = Auth.Token(token)
g = Github(auth = auth)
repo_name = "moni-netizen/gcsim-test"
repo = g.get_repo(repo_name)

mcp = FastMCP("CAB432 Assessment 2: Track B")
#region process-pr
@mcp.tool
def process_pull_request(pr_number: int) -> dict:
    """Process a pull request and summarise it.
    """
    try:
        pr = repo.get_pull(pr_number)
        username = pr.user.login
        state = pr.state
        title = pr.title
        body = pr.body

        return {"title": title, "body": body, "username": username, "state": state}
    except:
        return {"body": "No pull request found. Maybe it was the wrong number?"}
#endregion process-pr

@mcp.tool
def celsius_to_fahrenheit(celsius: float) -> str:
    """Convert a Celsius temperature to Fahrenheit.

    The decorator exposes this typed function as an MCP tool.
    """
    return f"{celsius:.1f}°C is 70°F"

@mcp.tool
def write_comment(id: int, response: str) -> dict:
    """Write a comment to this issue. I'm not actuall """
    issue = repo.get_issue(number = id)
    issue_comments = issue.get_comments()
    
    # check if a comment has already been written
    if issue_comments.totalCount == 0 and issue.state == "open":
        issue.create_comment(response)
        return {"status": 200, "body": "comment posted."}
            
    else:
        return {"status": 401, "body": "issue closed or already commented. disregard request."}


if __name__ == "__main__":
    mcp.run(show_banner = False)

