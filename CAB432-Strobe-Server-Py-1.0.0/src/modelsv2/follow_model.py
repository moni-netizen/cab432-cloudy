from __future__ import annotations

from typing import Any

from utils.id_generator import generate_id

import boto3
from boto3.dynamodb.conditions import Key

table_name = "n12023868-follows" 

dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)

table = dynamodb.Table(table_name)





def find_follow(follower_id: str, followee_id: str) -> dict[str, Any] | None:
    """Find follow and return it when available."""
    follow = table.get_item(
        Key = {
            "followerId": follower_id,
            "followeeId": followee_id
        }
    )
    
    return follow.get("Item")

def is_following(follower_id: str | None, followee_id: str) -> bool:
    """Return whether following is true for the current context."""
    if not follower_id:
        return False
    follow = find_follow(follower_id, followee_id)
    return bool(follow)
        
    
def get_following(user_id: str) -> list[str]:
    """Return following data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("followerId").eq(user_id)
    )

    followers = response.get("Items",[])
    return [users["followerId"] for users in followers]
    
    

def get_followers(user_id: str) -> list[str]:
    """Return followers data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("followeeId").eq(user_id)
    )
    followees = response.get("Items",[])

    return [user["followerId"] for user in followees]


def get_following_count(user_id: str) -> int:
    """Return following count data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("followerId").eq(user_id)
    )
    return response.get("Count", 0)

def get_follower_count(user_id: str) -> int:
    """Return follower count data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("followeeId").eq(user_id)
    )
    return response.get("Count", 0)


def create_follow(follow_data: dict[str, Any]) -> dict[str, Any]:
    """Create follow data and return the created payload."""
    follow = {
        "id": follow_data.get("id", generate_id()),
        "followerId": follow_data["followerId"],
        "followeeId": follow_data["followeeId"],
        "createdAt": follow_data.get("createdAt", now_iso()),
    }

    response = table.put_item(Item = follow)
    return response.get("Item")


def remove_follow(follower_id: str, followee_id: str) -> bool:
    """Remove follow data for the requested context."""
    follows_to_delete = table.delete_item(
        Key = {
            "followerId": follower_id,
            "followeeId": followee_id
        }
    )
    
    return True


def remove_follows_by_user_id(user_id: str) -> None:
    """Remove follows by user id data for the requested context."""
    followers_to_delete = table.query(
        KeyConditionExpression = Key("followerId").eq(user_id)
    ).get("Items", [])
    followees_to_delete = table.query(
        KeyConditionExpression = Key("followeeId").eq(user_id)
    ).get("Items", [])

    with table.batch_writer() as batch:
        for ids in followers_to_delete + followees_to_delete:
            batch.delete_item(
                Key = {
                    "followerId": ids["followerId"],
                    "followeeId": ids["followeeId"]
                }
            )

    return True

    

