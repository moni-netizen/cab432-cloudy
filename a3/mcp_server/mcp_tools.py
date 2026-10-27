from __future__ import annotations
# this is meant to hold the MCP server (for now) and define my toolkit


from fastmcp import FastMCP
import boto3
from botocore.exceptions import ClientError
import json

from botocore.exceptions import ClientError
from mcp.server.auth.provider import AccessToken, TokenVerifier
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

# for page retrieval
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlsplit, unquote

# my super scummy PAT storage (sorry)
def get_secret() -> dict:

    secret_name = "n12023868-a3-secrets"
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


#region s3vector-config
aws_region = "ap-southeast-2"
bucket_name = "n12023868-pages"  
index = "stardew-valley"

#region s3_vectors & bedrock
bedrock = boto3.client("bedrock-runtime", region_name = aws_region)
s3vectors = boto3.client("s3vectors", region_name = aws_region)

# this is to embed our question to properly query s3
titan_model_id = "amazon.titan-embed-image-v1"
DIMENSION = 256

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

mcp = FastMCP("CAB432 Assessment 3: Steam MCP Server",
 auth=verifier)

#endregion github-configuration

#endregion s3_vectors & bedrock
@mcp.tool
def answer_question(question: str) -> list:
    # create an embedding for our response
    embedding = embed_question(question)

    # query the s3vector
    matching_links = search_s3(embedding)

    # retrieve page body
    responses = []
    for urls in matching_links:
        page_info = read_page(urls)
        responses.append(page_info)

    # return to bot
    return responses

#region helper-functions
def create_embedding(payload: dict) -> list[float]:
    """Return one 256-dimensional Titan Multimodal embedding."""
    # Bedrock creates the embedding; S3 Vectors stores and searches it.
    response = bedrock.invoke_model(
        modelId=titan_model_id,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )
    return json.loads(response["body"].read())["embedding"]
 

def embed_question(question: str) -> list[float]:
    """embeds our question! returns the actual embedding """

    # get the issue info
    try:
        contents = {
            "inputText": question,
            "embeddingConfig": {"outputEmbeddingLength": DIMENSION}
        }

        embedding = create_embedding(contents)
        return embedding
    except:
        return None


def search_s3(embedding: list[float]) -> list:
    """using our embedding, find the top 3 matches that might best answer 
    our question. yay! returns them as a list of urls """
    result = s3vectors.query_vectors(
        vectorBucketName=bucket_name,
        indexName=index,
        queryVector={"float32": embedding},
        topK=3,
        returnDistance=True,
        returnMetadata=True,
    )
    vectors = result.get("vectors",[])
    top_matches = []

    if len(vectors) > 0:
        for vector in vectors:
            top_matches.append(vector.get("metadata").get("url"))
    return top_matches


def get_article_html(url: str) -> str:
    """using our urls, we want to see its contents, this requests the html 
    of the url supplied """
    parsed = urlsplit(url)

    if not parsed.path.startswith("/wiki/"):
        raise ValueError(f"Expected a /wiki/ article URL: {url}")

    page_title = unquote(parsed.path[len("/wiki/"):])

    response = requests.get(
        "https://stardewvalley.fandom.com/api.php",
        params={
            "action": "parse",
            "page": page_title,
            "prop": "text",
            "redirects": 1,
            "format": "json",
            "formatversion": 2,
        },
        headers={"User-Agent": "WikiContentWorker/1.0"},
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"MediaWiki API error: {data['error']}")

    return data["parse"]

# using the html output, we want to prettify and process it.
def read_page(link: str) -> dict:
    """calls get_article_html to just read the page and spit its url, title 
    and text luh calm chill shi"""
    data = get_article_html(link)
    soup = BeautifulSoup(data["text"], "html.parser")

    for element in soup(["script", "style"]):
        element.decompose()

    text = " ".join(soup.get_text(separator=" ", strip=True).split())

    return {
        "url": link,
        "title": data["title"],
        "text": text
    }
#endregion helper-functions





if __name__ == "__main__":
   mcp.run(show_banner=False, transport="streamable-http", host="0.0.0.0", port=8080)

