from __future__ import annotations
# this is meant to hold the MCP server (for now) and define my toolkit
from github import Github
from fastmcp import FastMCP
import boto3

# my super scummy PAT storage (sorry)
token = "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"
g = Github(token)

# retrieve our repo
repo_name = "moni-netizen/gcsim-fork"
repo = g.get_repo(repo_name)

#region server-identity
# This server name is shown to an MCP client during connection.
mcp = FastMCP("CAB432 Assessment 2: Track B")
#endregion server-identity

#region s3_vector housing
REGION = "ap-southeast-2"
BUCKET = "n12023868-issues-vector"
INDEX = "lodged_issues"

DIMENSION = 256
TITAN_MULTIMODAL_MODEL_ID = "amazon.titan-embed-image-v1"
VISION_MODEL_ID = "google.gemma-3-12b-it"
#endregion s3_vector housing

#region initialise bucket

def ensure_index(client: boto3.client) -> None:
    """Create our vector bucket and index!"""
    tags = {"qut-username": "n12023868@qut.edu.au", "purpose": "assessment 2"}

    try:
        # A vector bucket is the top-level container for one or more indexes.
        client.create_vector_bucket(vectorBucketName=BUCKET, tags=tags)
        print(f"Created vector bucket {BUCKET}")
    except client.exceptions.ConflictException:
        print(f"Using existing vector bucket {BUCKET}")

    try:
        # An index fixes the data type, dimension, and similarity metric.
        client.create_index(
            vectorBucketName=BUCKET,
            indexName=INDEX,
            dataType="float32",
            dimension=DIMENSION,
            distanceMetric="cosine", #potentially experiment w/ different metrics!
            tags=tags,
        )
        print(f"Created vector index {INDEX}")
    except client.exceptions.ConflictException:
        print(f"Using existing vector index {INDEX}")

#endregion initialise bucket

#region embed-with-titan
def invoke_titan(client: boto3.client, payload: dict) -> list[float]:
    """Return one 256-dimensional Titan Multimodal embedding."""
    # Bedrock creates the embedding; S3 Vectors stores and searches it.
    response = client.invoke_model(
        modelId=TITAN_MULTIMODAL_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )
    return json.loads(response["body"].read())["embedding"]


def embed_text(client: boto3.client, text: str) -> list[float]:
    """Embed a text into the vector space."""
    return invoke_titan(
        client,
        {"inputText": text, "embeddingConfig": {"outputEmbeddingLength": DIMENSION}},
    )


def embed_image(client: boto3.client, image_path: Path) -> list[float]:
    """Embed an image into vector space """
    # Titan expects the image bytes as base64 text in this request format.
    image_base64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
    return invoke_titan(
        client,
        {"inputImage": image_base64, "embeddingConfig": {"outputEmbeddingLength": DIMENSION}},
    )
#endregion embed-with-titan


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

# second tool! find similar issues to new issues and write a suggested troubleshooting response
# well, it'll find items in s3 and use it as a precedent to write a response.

#region find_similar_issues
@mcp.tool
def find_similar_issues():
    """This will retrieve the three most similar results and return them to the bot.
       Our assistant will then process these issues and write a comment to the issue.  """
    a

#endregion find_similar_issues

""" i not done
 i so tired i go o bed"""

# tool three! store an issue and the generated response into the s3 vector to improve memory
# i guess? just so out future responses are more informed. 

#region store_issue
def store_issue():
    """Store a message into Amazon S3 vectors. This will submit images of pull 
       requests and also like... text descriptions i guess? This gets called after find_similar_issues
       to ensure we retrieve the AI's response and any images."""

       # as this is also a post, make a check to dtm whether this new issue has already been populated
       # into the vector database. check PR number
    a

#endregion store_issue

# tool four! write the suggested troubleshooting response to 

#region write_comment
def write_comment():
    a
    # make sure that this command has a check to dtm whether moni-netizen-ai has already written a response.
    # this will enforce idempotency -> multiple requests will do the same thing every time i guess? 
#endregion write_comment

if __name__ == "__main__":
    #region stdio-transport
    # Start the stdio protocol loop; do not print ordinary output to stdout.
    mcp.run(transport = "stdio", show_banner = False)
    #endregion stdio-transport
