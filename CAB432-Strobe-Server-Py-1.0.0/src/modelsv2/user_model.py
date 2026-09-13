from __future__ import annotations

from typing import Any
import boto3
from boto3.dynamodb.conditions import Key

from id_generator import generate_id

## connecting the dynamodb table
table_name = "n12023868-users" 

dynamodb = boto3.resource(
    "dynamodb",
    region_name = "ap-southeast-2"
)

table = dynamodb.Table(table_name)

def _users() -> list[dict[str, Any]]:
    """Return the mutable users collection from the database."""
    all_items = []
    response = table.scan()
    all_items.extend(response.get('Items', []))

    return all_items

def sanitize_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a user object without sensitive authentication fields."""
    if user is None:
        return None
    sanitized = dict(user)
    sanitized.pop("password", None)
    return sanitized


def find_user_by_id(user_id: str) -> dict[str, Any] | None:
    """Find user by id and return it when available."""
    user = table.get_item(
            Key = {
                "userId": user_id
            }
        )
    
    return sanitize_user(user.get("Item"))


def find_user_auth_by_email(email: str) -> dict[str, Any] | None:
    """Find user auth by email and return it when available."""
    user = table.query(
        KeyConditionExpression = Key("email").eq(email)
    )
    return user.get("Item")


def get_all_users() -> list[dict[str, Any]]:
    """Return all users data for the requested context."""
    all_items = _users()
    
    return [sanitize_user(user) for user in all_items]



def create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    """Create user data and return the created payload."""
    user = {
        "userId": user_data.get("id", generate_id()),
        "username": user_data["username"],
        "email": user_data["email"],
        "password": user_data["password"],
        "role": user_data.get("role", "user"),
        "createdAt": user_data.get("createdAt", now_iso()),
        "updatedAt": user_data.get("updatedAt", now_iso()),
    }
    response = table.put_item(Item = user)

    return sanitize_user(response.get("Item"))


def update_user(user_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
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
        Key = {"userId": user_id}, 
        UpdateExpression = update_expression,
        ExpressionAttributeNames = expression_attribute_names,
        ExpressionAttributeValues = expression_attribute_values
    )

    return response


def delete_user(user_id: str) -> bool:
    """Delete user data for the requested context."""
    response = table.delete_item(
        Key = {
            "userId": user_id
        }
    )
    return True


def username_exists(username: str) -> bool:
    """Return whether a username already exists in storage."""
    response = table.query(
        Key("username").eq(username)
    )

    if len(response) > 0:
         return True
    else:
        return False


def email_exists(email: str) -> bool:
    """Return whether an email address already exists in storage."""
    response = table.query(
        Key("email").eq(email)
    )

    if len(response) > 0:
        return True
    else:
        return False

## ask about this section what the heeelllll
def search_users(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search users records using the provided filters."""
    if not query:
        return get_all_users()[:limit]
    lowered = query.lower()

    matches = [user for user in _users() if lowered in user["username"].lower()]
    return [sanitize_user(user) for user in matches[:limit]]


def delete_user_with_cascade(user_id: str) -> bool:
    """Delete user with cascade data for the requested context."""
    if not table.get_item(Key = {"userId": user_id}):
        return False

    from comment_model import delete_comments_by_post_id
    from follow_model import remove_follows_by_user_id
    from like_model import remove_likes_by_user_id
    from moment_model import delete_moments_by_user_id
    from post_model import delete_posts_by_user_id, get_posts_by_user_id

    posts = get_posts_by_user_id(user_id, limit=10_000, offset=0)
    delete_posts_by_user_id(user_id)
    remove_likes_by_user_id(user_id)
    remove_follows_by_user_id(user_id)
    delete_moments_by_user_id(user_id)

    for post in posts:
        delete_comments_by_post_id(post["postId"])

    response = table.delete_item(
        Key ={"userId": user_id}
    )
    
    return True

