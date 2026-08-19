from __future__ import annotations

import boto3
from boto3.dynamodb.conditions import Key
from typing import Any

from ..utils.id_generator import generate_id # fix later

## connecting the dynamodb table
table_name = "n12023868-comments" 

dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)

table = dynamodb.Table(table_name)


def find_comment_by_id(comment_id: str) -> dict[str, Any] | None:
    """Find moment by id and return it when available."""
    response = table.query(
        KeyConditionExpression = Key("commentId").eq(comment_id)
    )

    return response.get("Items", [])

def get_comments_by_post_id(post_id: str) -> list[dict[str, Any]]:
    """Return comments by post id data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("postId").eq(post_id)
    )

    return response.get("Items", [])


def create_comment(comment_data: dict[str, Any]) -> dict[str, Any]:
    """Create comment data and return the created payload."""
    comment = {
        "commendId": comment_data.get("id", generate_id()),
        "postId": comment_data["postId"],
        "userId": comment_data["userId"],
        "text": comment_data["text"],
        "createdAt": comment_data.get("createdAt", now_iso()),
        "updatedAt": comment_data.get("updatedAt", now_iso()),
    }
    table.put_item(Item = comment)
    
    return comment


def delete_comment(comment_id: str) -> bool:
    """Delete comment data for the requested context."""
    comment = find_comment_by_id(comment_id)
    table.delete_item(Item = comment)
    return True


def get_comment_count_by_post_id(post_id: str) -> int:
    """Return comment count by post id data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("postId").eq(post_id)
    )

    return response.get("count", 0)

def delete_comments_by_post_id(post_id: str) -> None:
    """Delete comments by post id data for the requested context."""
    comments = get_comments_by_post_id(post_id)

    with table.batch_writer() as batch:
        for key in comments:
            batch.delete_item(
                Key = {
                    "commentId": key["commentId"]
                }
            )

    return True

