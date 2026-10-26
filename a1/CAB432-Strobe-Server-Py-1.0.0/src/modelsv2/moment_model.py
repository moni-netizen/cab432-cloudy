from __future__ import annotations

import boto3
from boto3.dynamodb.conditions import Key

from typing import Any

from id_generator import generate_id # do this later

table_name = "n12023868-moments" 

dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)

table = dynamodb.Table(table_name)

def create_moment(moment_data: dict[str, Any]) -> dict[str, Any]:
    """Create a DynamoDB entry and return the created item."""
    record = {
        "momentId": moment_data.get("momentId", generate_id()),
        "userId": moment_data["userId"],
        "imageUrl": moment_data["imageUrl"],
        "caption": moment_data.get("caption", ""),
        "status": moment_data.get("status", "active"),
        "hiddenBy": moment_data.get("hiddenBy"),
        "hiddenAt": moment_data.get("hiddenAt"),
        "archivedAt": moment_data.get("archivedAt"),
        "createdAt": moment_data.get("createdAt", now_iso()),
        "expiresAt": moment_data.get("expiresAt"),
        "updatedAt": moment_data.get("updatedAt", now_iso()),
    }

    response = table.put_item(Item = record)
    return response

def find_moment_by_id(moment_id, user_id):
    """Find moment by id and return it when available."""
    response = table.get_item(
        Key = {
                "momentId": moment_id,
                "userId": user_id
              }
    )

    return response.get("Item")

def update_moment(moment_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    """Update moment and return the updated payload."""
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
        Key = {"momentId": moment_id}, 
        UpdateExpression = update_expression,
        ExpressionAttributeNames = expression_attribute_names,
        ExpressionAttributeValues = expression_attribute_values
    )

    return response
    

def delete_moment(moment_id, user_id):
    """Delete moment data for the requested context"""
    response = table.delete_item(
        Key = {
            "momentId": moment_id,
            "userId": user_id
        }
    )

    return response

def get_moments_by_user_ids(user_ids: list[str]) -> list[dict[str, Any]]:
    """Return moments by user ids data for the requested context."""

    keys_list = [{"userId": user_id} for user_id in user_ids]
    response = table.batch_get_item(
        RequestItems = {
            "Keys": keys_list
        }
    )

    return response.get("Items", [])

def get_moments_by_user_id(user_id: str) -> list[dict[str, Any]]:
    """Return moments by user id data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    )

    return response.get("Items", [])

def delete_moments_by_user_id(user_id: str) -> bool:
    """Delete moments by user id data for the requested context."""
    moments_to_delete = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    ).get("Items", [])
    
    with table.batch_writer() as batch:
        for key in moments_to_delete:
            batch.delete_item(
                Key = {
                    "momentId": key["momentId"]
                }
            )
    
    return True
