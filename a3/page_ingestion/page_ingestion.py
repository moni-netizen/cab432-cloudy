from __future__ import annotations

import json, os, logging
import requests
from bs4 import BeautifulSoup

from urllib.parse import urlsplit, unquote

import boto3
from botocore.exceptions import ClientError

aws_region = "ap-southeast-2"
sqs_queue_url = "https://sqs.ap-southeast-2.amazonaws.com/901444280953/n12023868-wiki-pages-queue"
sqs = boto3.client("sqs")

response = sqs.receive_message(
    QueueUrl = sqs_queue_url,
    MaxNumberOfMessages = 1,
    WaitTimeSeconds = 15
)

# for embeddings
bedrock = boto3.client("bedrock-runtime", region_name = aws_region)
titan_model = "amazon.titan-embed-image-v1"
dimension = 256



# for s3vectors
s3vectors = boto3.client("s3vectors", region_name = aws_region)
s3_vector_name = "n12023868-pages"
index_name = "stardew-valley"

# for dynamodb
table_name = "n12023868-wiki-pages"
dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)
table = dynamodb.Table(table_name)

# the pipeline to process ONE page
def process_page(payload: dict) -> tuple[int, dict]:
    try:
        # get some baka page info
        page_info = read_page(payload.get("url"))

        # store the page
        response = store_to_s3(page_info)
        if response:
            # store to dynamodb
            aa

        # return ??
        return 200, page_info
    
    except:
        return 400, {"message": "kil yourself"}
        print("they hit the pentagon...")


# gets the HTML of an article using a url
def get_article_html(url: str) -> str:
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

# creates an embedding using titan
def create_embedding(payload: dict) -> list[float]:
    """Return one 256-dimensional Titan Multimodal embedding."""
    # Bedrock creates the embedding; S3 Vectors stores and searches it.
    print("reached the create embedding")
    try:
        response = bedrock.invoke_model(
            modelId=titan_model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        return json.loads(response["body"].read())["embedding"]
    except Exception as e:
        print(e)
        return []

# embeds the page using create_embedding
def embed_page(payload: dict) -> list[float]:
    embedding = {
        "inputText": f"{payload["title"]}-{payload["text"]}",
        "embeddingConfig": {"outputEmbeddingLength" : dimension}
    }

    embed = create_embedding(embedding)
    print("embed created!")
    return embed

# uses page info to create an embedding and store it to s3vectors
def store_to_s3(page_info: dict):
    embedding = embed_page(page_info)
    try:
        s3vectors.put_vectors(
        vectorBucketName = s3_vector_name,
        indexName = index_name,
        vectors = [
            {
                "key": f"{page_info["url"]}-{page_info["title"]}",
                "data": {"float32": embedding},
                "metadata": {"url": page_info["url"], "title": page_info["title"]}
            }
        ])
        return "saved"
    
    except Exception as e:
        return None

# updates the dynamodb table status
def update_status():
    aa



# gets all the links from the queue! i checked, theres 20
message = response.get("Messages", [])[0]
page_list = json.loads(message["Body"])

code, page_info = process_page(page_list[1])

print(code)