# this is meant to hold the MCP server (for now) and define my toolkit
from github import Github
from fastmcp import FastMCP

# my super scummy PAT storage (sorry)
token = "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"
g = Github(token)

# retrieve our repo
repo_name = "PyGithub/PyGithub"
repo = g.get_repo(repo_name)

#region server-identity
# This server name is shown to an MCP client during connection.
mcp = FastMCP("CAB432 Assessment 2: Track B")
#endregion server-identity


#my first tool! summarise PR, provide date & user

#region process-pr
@mcp.tool
def process_pull_request(pr_number: int) -> dict:
    """Process a pull request and summarise it.
    """
    pr = repo.get_pull(pr_number)
    username = pr.user.login
    state = pr.state
    body = pr.body

    return {"body": body, "username": username, "state": state}
#endregion process-pr


if __name__ == "__main__":
    #region stdio-transport
    # Start the stdio protocol loop; do not print ordinary output to stdout.
    mcp.run(transport = "stdio", show_banner = False)
    #endregion stdio-transport
