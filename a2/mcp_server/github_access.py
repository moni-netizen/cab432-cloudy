from __future__ import annotations
# this is meant to hold the MCP server (for now) and define my toolkit
from github import Auth, Github
from fastmcp import FastMCP
import boto3
import json
from botocore.exceptions import ClientError
from mcp.server.auth.provider import AccessToken, TokenVerifier
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

# my super scummy PAT storage (sorry)
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

#region github-configuration
secrets = get_secret()

MCP_SHARED_TOKEN = secrets["MCP_SHARED_TOKEN"]

verifier = StaticTokenVerifier(
    tokens={
        MCP_SHARED_TOKEN: {
            "client_id": "acp-agent",
            "scopes": ["mcp"],
        },
    },
)
mcp = FastMCP("CAB432 Assessment 2: Track B",
 auth=verifier)

token = secrets["GITHUB_PAT"]
auth = Auth.Token(token)
g = Github(auth = auth)

repo_name = "moni-netizen/gcsim-test"
repo = g.get_repo(repo_name)
#endregion github-configuration

#region s3vector-config
REGION = "ap-southeast-2"
BUCKET = "n12023868-issues-vector"  
INDEX = "lodged-issues"

TITAN_MULTIMODAL_MODEL_ID = "amazon.titan-embed-image-v1"
DIMENSION = 256
# option if i want to add gemma since im using fricken nemotron
#VISION_MODEL_ID = "google.gemma-3-12b-it"
#endregion s3vector config

#region s3_vectors & bedrock
bedrock = boto3.client("bedrock-runtime", region_name = REGION)
s3vectors = boto3.client("s3vectors", region_name = REGION)
#endregion s3_vectors & bedrock

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
def write_comment(id: int, response: str) -> dict:
    """Write a comment to this issue. I'm not actuall """
    try:
        issue = repo.get_issue(number = id)
        issue_comments = issue.get_comments()
        
        # check if a comment has already been written
        if issue_comments.totalCount == 0 and issue.state == "open":
            issue.create_comment(response)
            return {"status": 200, "body": "comment posted."}
                
        else:
            return {"status": 401, "body": "issue closed or already commented. disregard request."}
    except:
        return {"status": 400, "body": "error during calculations."}

@mcp.tool
def check_and_store(issue_id: int) -> list:
    """
    Finds similar issues to that of our current issue_id, and stores
    info inside the s3 vector base for future queries. 
    """
    try:
        similar_issues = find_similar_issues(issue_id)
        issue_info, embeddings = embed_issue(issue_id)

        store_issue(issue_info, embeddings)
        return(similar_issues)
    except:
        return([])

#region helper-functions
def invoke_titan(payload: dict) -> list[float]:
    """Return one 256-dimensional Titan Multimodal embedding."""
    # Bedrock creates the embedding; S3 Vectors stores and searches it.
    response = bedrock.invoke_model(
        modelId=TITAN_MULTIMODAL_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )
    return json.loads(response["body"].read())["embedding"]
 
def embed_issue(id: int) -> tuple[dict, list[float]]:
    """Embed an issue body into the vector space. im pre sure the string 'text' 
       will need to be changed at some point to... something related to the issue"""

    # get the issue info
    try:
        issue = repo.get_issue(id) 

        issue_info = {
                        "issueNo": id,
                        "title": issue.title,
                        "url": issue.html_url
                    }

        return issue_info, invoke_titan(
            {"inputText": f"{issue.title}-{issue.body}", "embeddingConfig": {"outputEmbeddingLength": DIMENSION}},
        )
    except:
        return{"statusCode":400, "body": "issue not found"}, None

def store_issue(issue_info: dict, embedding: list[float]) -> None:
    """Store a message into Amazon S3 vectors. This will submit images of pull 
       requests and also like... text descriptions i guess? This gets called after find_similar_issues
       to ensure we retrieve the AI's response and any images."""
    
    # add this new issue into the s3 vector bucket
    s3vectors.put_vectors(
        vectorBucketName = BUCKET,
        indexName = INDEX,
        vectors = [
            {
                "key": f"issue-{issue_info.get("issueNo")}",
                "data": {"float32": embedding},
                "metadata": issue_info  
            }
        ]
    )

def find_similar_issues(issue_id: int) -> list:
    """This will retrieve the three most similar results and return them to the bot.
       Our assistant will then process these issues and write a comment to the issue.  """

    info, embedding = embed_issue(issue_id)
  
    result = s3vectors.query_vectors(
        vectorBucketName=BUCKET,
        indexName=INDEX,
        queryVector={"float32": embedding},
        topK=3,
        returnDistance=True,
        returnMetadata=True,
    )
    vectors = result.get("vectors",[])
    matching_ids = []

    if len(vectors) > 0:
        for vector in vectors:
            matching_ids.append(vector.get("metadata").get("issueNo"))

    # returns the three most similar issues by issue number        
    return(return_bodies(matching_ids))

def return_bodies(items: list) -> list:
    payload = []
    for item in items:
        issue = repo.get_issue(number = item)
        issue_body = issue.body
        comments = [
            {"user": c.user.login, "body": c.body, "created_at": c.created_at.isoformat()}
            for c in issue.get_comments()
        ]
        payload.append({"body": issue_body, "comments": comments})
    
    return payload

#endregion helper-functions





if __name__ == "__main__":
   mcp.run(show_banner=False, transport="streamable-http", host="0.0.0.0", port=8000)

