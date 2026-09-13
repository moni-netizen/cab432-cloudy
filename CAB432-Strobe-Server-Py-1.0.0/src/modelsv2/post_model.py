from __future__ import annotations

import boto3
from boto3.dynamodb.conditions import Key
from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist

table_name = "n12023868-posts" 

dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)

table = dynamodb.Table(table_name)

def _posts() -> list[dict[str, Any]]:
    """Return the mutable posts collection from the database."""
    return db()["posts"]


def find_post_by_id(post_id: str) -> dict[str, Any] | None:
    """Find post by id and return it when available."""
    response = table.query(
        KeyConditionExpression = Key("postId").eq(post_id)
    )
    return response.get("Item")


def get_posts_by_user_id(user_id: str, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return posts by user id data for the requested context."""

    all_matches = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    )
    

    all_matches.sort(key=lambda post: post["createdAt"], reverse=True)
    return all_matches[offset:offset + limit]


def get_all_posts(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return all posts data for the requested context."""
    all_items = []
    response = table.scan()

    all_items.extend(response.get("Items", []))

    all_items.sort(key=lambda post: post["createdAt"], reverse=True)
    return all_items[offset:offset + limit]


def create_post(post_data: dict[str, Any]) -> dict[str, Any]:
    """Create post data and return the created payload."""
    post = {
        "id": post_data.get("id", generate_id()),
        "userId": post_data["userId"],
        "title": post_data["title"],
        "description": post_data.get("description", ""),
        "images": list(post_data.get("images", [])),
        "status": post_data.get("status", "active"),
        "hiddenBy": post_data.get("hiddenBy"),
        "hiddenAt": post_data.get("hiddenAt"),
        "createdAt": post_data.get("createdAt", now_iso()),
        "updatedAt": post_data.get("updatedAt", now_iso()),
    }
    response = table.put_item(Item = post)
    return response.get("Item")


def update_post(post_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update post and return the updated payload."""
    user_id = find_post_by_id(post_id).get("userId")

    fields = {
    key: value
    for key, value in updates.items()
    if value is not None and key !="momentId"
    }
    fields["updatedAt"] = now_iso()

    update_expression_parts = []
    expression_attribute_names = {}
    expression_attribute_values = {}

    for key,value in fields.items():
        name_placeholder = f"#{key}"
        value_placeholder = f":{key}"
        update_expression_parts.append(f"{name_placeholder} = {value_placeholder}")
        expression_attribute_names[name_placeholder] = key
        expression_attribute_values[value_placeholder] = value

    update_expression = "SET " + ", ".join(update_expression_parts)

    response = table.update_item(
        Key = {"userId": user_id, 
                "postId": post_id}, 
        UpdateExpression = update_expression,
        ExpressionAttributeNames = expression_attribute_names,
        ExpressionAttributeValues = expression_attribute_values
    )

    return response
   


def delete_post(post_id: str) -> bool:
    """Delete post data for the requested context."""
    user_id = find_post_by_id(post_id).get("userId")

    response = table.delete_item(
        Key = {
            "userId": user_id,
            "postId": post_id
        }
    )
    
    return response


def get_posts_from_users(user_ids: list[str], limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    """Return posts from users data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    )

    posts = response.get("Items", [])
    posts.sort(key=lambda post: post["createdAt"], reverse=True)
    return posts[offset:offset + limit]


def get_post_count_by_user_id(user_id: str) -> int:
    """Return post count by user id data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    )
    return response.get("count", 0)



def delete_posts_by_user_id(user_id: str) -> None:
    """Delete posts by user id data for the requested context."""
    posts_to_delete = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    )

    with table.batch_writer() as batch:
        for posts in posts_to_delete:
            batch.delete_item(Key = posts)

    return True 

    

