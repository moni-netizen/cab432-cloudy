import json, os, logging
import boto3
from botocore.exceptions import ClientError

sqs_queue_url = "https://sqs.ap-southeast-2.amazonaws.com/901444280953/n12023868-wiki-pages-queue"
sqs = boto3.client("sqs")

response = sqs.receive_message(
    QueueUrl = sqs_queue_url,
    MaxNumberOfMessages = 1,
    WaitTimeSeconds = 15
)

bodies = []
# gets all the links from the queue! i checked, theres 20
for message in response.get("Messages", []):
    body = message["Body"]
    bodies.append(body)
    
def process_page(payload: dict):
    try:
        aa
    
    except:
        aa

def read_page(link: str):
    a