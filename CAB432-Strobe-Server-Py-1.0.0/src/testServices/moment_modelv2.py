## relevant database operations for the moment type

from __future__ import annotations
import boto3
from boto3.dynamodb.conditions import Key

from typing import Any

from ..utils.id_generator import generate_id
from .common import copy_record, db, now_iso, persist

# get the dynamoDB table
table_name = "n12023868-a1-moments"

dynamodb = boto3.resource(
    "dynamodb",
    region_name="ap-southeast-2"
)

table = dynamodb.Table(table_name)

# def _moments() -> list[dict[str, Any]]:
#     """Return the mutable moments collection from the database."""
#     return db()["moments"]

## this is for GET /v1/moments/feed i think...
def _moments() -> list[dict[str, Any]]:
    """Using dynamoDB, return all the moments from the database."""
    # Initialize an empty list to store all records
    all_items = []

    # Perform the initial scan
    response = table.scan()
    all_items.extend(response.get('Items', []))

    return all_items

# def create_moment(moment_data: dict[str, Any]) -> dict[str, Any]:
#     """Create moment data and return the created payload."""
#     moment = {
#         "id": moment_data.get("id", generate_id()),
#         "userId": moment_data["userId"],
#         "imageUrl": moment_data["imageUrl"],
#         "caption": moment_data.get("caption", ""),
#         "status": moment_data.get("status", "active"),
#         "hiddenBy": moment_data.get("hiddenBy"),
#         "hiddenAt": moment_data.get("hiddenAt"),
#         "archivedAt": moment_data.get("archivedAt"),
#         "createdAt": moment_data.get("createdAt", now_iso()),
#         "expiresAt": moment_data.get("expiresAt"),
#         "updatedAt": moment_data.get("updatedAt", now_iso()),
#     }
#     _moments().append(moment)
#     persist()
#     return copy_record(moment)

# this is for the POST /v1/moments API
def create_moment(moment_data: dict[str, Any]) -> dict[str, Any]:
    """Create a DynamoDB entry and return the created item."""
    record = {
        "id": moment_data.get("id", generate_id()),
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

    table.put_item(Item = record)
    print("Item inserted.")
    return copy_record(record)


# def find_moment_by_id(moment_id: str) -> dict[str, Any] | None:
#     """Find moment by id and return it when available."""
#     return copy_record(next((moment for moment in _moments() if moment["id"] == moment_id), None))

# is meant to be the query or GET
def find_moment_by_id(moment_id: str) -> dict[str, Any] | None:
    """Find moment by id and return it when available."""
    response = table.query(
        KeyConditionExpression = Key("momentId").eq(moment_id)
    )

    print(response["Items"])


# def update_moment(moment_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
#     """Update moment and return the updated payload."""
#     for moment in _moments():
#         if moment["id"] == moment_id:
#             for key, value in updates.items():
#                 if value is not None and key != "id":
#                     moment[key] = value
#             moment["updatedAt"] = now_iso()
#             persist()
#             return copy_record(moment)
#     return None

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

    update_expression = "SET" + ", ".join(update_expression_parts)

    response = table.update_item(
        Key = {"momentId": moment_id}, 
        UpdateExpression = update_expression,
        ExpressionAttributeNames = expression_attribute_names,
        ExpressionAttributeValues = expression_attribute_values
    )

    return None


# def delete_moment(moment_id: str) -> bool:
#     """Delete moment data for the requested context."""
#     moments = _moments()
#     index = next((i for i, moment in enumerate(moments) if moment["id"] == moment_id), None)
#     if index is None:
#         return False
#     del moments[index]
#     persist()
#     return True


def delete_moment(moment_id: str) -> bool:
    """Delete moment data for the requested context"""
    response = table.delete_item(
        Key = {
            "momentId": moment_id
        }
    )


# def get_moments_by_user_ids(user_ids: list[str]) -> list[dict[str, Any]]:
#     """Return moments by user ids data for the requested context."""
#     moments = [copy_record(moment) for moment in _moments() if moment["userId"] in user_ids]
#     moments.sort(key=lambda moment: moment["createdAt"], reverse=True)
#     return moments

def get_moments_by_user_ids(user_ids: list[str]) -> list[dict[str, Any]]:
    """Return moments by user ids data for the requested context."""
    keys_list = [{"userId": user_id} for user_id in user_ids]
    response = table.batch_get_item(
        RequestItems = {
            "Keys": keys_list
        }
    )

    return response

# def get_moments_by_user_id(user_id: str) -> list[dict[str, Any]]:
#     """Return moments by user id data for the requested context."""
#     return get_moments_by_user_ids([user_id])

def get_moments_by_user_id(user_id: str) -> list[dict[str, Any]]:
    """Return moments by user id data for the requested context."""
    response = table.query(
        KeyConditionExpression = Key("userId").eq(user_id)
    )

    return response 




# def delete_moments_by_user_id(user_id: str) -> None:
#     """Delete moments by user id data for the requested context."""
#     db()["moments"] = [moment for moment in _moments() if moment["userId"] != user_id]
#     persist()

def delete_moments_by_user_id(user_id: str) -> None:
    """Delete moments by user id data for the requested context."""
    moments = get_moments_by_user_id(user_id).get("Items", [])
    
    with table.batch_writer() as batch:
        for key in moments:
            batch.delete_item(
                Key = {
                    "momentId": key["momentId"]
                }
            )



