from __future__ import annotations

from typing import Any

from utils.id_generator import generate_id
import boto3
from boto3.dynamodb.conditions import KeyConditionExpression

table_name = "n12023868-likes" 

dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)

table = dynamodb.Table(table_name)


def find_like(post_id: str, user_id: str) -> dict[str, Any] | None:
    """Find like and return it when available."""
    response = table.get_item(
        Key = {
            "postId": post_id,
            "userId": user_id
        }
    )
    return response.get("Item", None)
    


def has_user_liked_post(post_id: str, user_id: str | None) -> bool:
    """Return whether user liked post exists for the current context."""
    if not user_id:
        return False
    response = table.get_item(
        Key = {
            "postId": post_id,
            "userId": user_id
        }
    )

    return bool(response)
    


def get_like_count_by_post_id(post_id: str) -> int:
    """Return like count by post id data for the requested context."""
    likes = table.query(
        KeyConditionExpression = Key("postId").eq(post_id)
    )
    return likes.get("Count", 0)


def create_like(like_data: dict[str, Any]) -> dict[str, Any]:
    """Create like data and return the created payload."""
    like = {
        "id": like_data.get("id", generate_id()),
        "postId": like_data["postId"],
        "userId": like_data["userId"],
        "createdAt": like_data.get("createdAt", now_iso()),
    }

    response = table.put_item(
        Item = like
    )
    
    return like


def remove_like(post_id: str, user_id: str) -> bool:
    """Remove like data for the requested context."""
    response = table.delete_item(
        Key = {
            "postId": post_id,
            "userId": user_id
        }
    )
    
    if response is None:
        return False
   
    return True


def remove_likes_by_post_id(post_id: str) -> None:
    """Remove likes by post id data for the requested context."""
    likes_to_delete = table.query(
        KeyConditionExpression = Key("postId").eq(post_id)
    ).get("Items", [])

    with table.batch_writer() as batch:
        for likes in likes_to_delete:
            batch.delete_item(
                Key = {
                    "postId": likes["postId"],
                    "userId": likes["userId"]
                }
            )
    


def remove_likes_by_user_id(user_id: str) -> None:
    """Remove likes by user id data for the requested context."""
    likes_to_delete = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    ).get("Items", [])

    with table.batch_writer() as batch:
        for likes in likes_to_delete:
            batch.delete_item(
                Key = {
                    "postId": likes["postId"],
                    "userId": likes["userId"]
                }
            )

