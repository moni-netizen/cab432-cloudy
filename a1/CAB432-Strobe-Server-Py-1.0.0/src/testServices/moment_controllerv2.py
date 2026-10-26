from __future__ import annotations

from ..services.moment_service import create_moment, delete_moment, get_moment_archive, get_moment_feed, hide_moment

def create_moment_controller(event):
    """Create a moment and shape the HTTP response payload."""
    body = json.loads(event["body"])
    result = create_moment(body["userId"], body)
    return 201, {"message": "Moment created successfully", "moment": json.dumps(result)}


def get_moment_feed_controller(event):
    """Fetch active moment feed and shape the HTTP response payload."""
    updates = json.loads(event["body"])
    user_id = updates.get("userId")
    user_role = "moderator" # for now, not forever
    moments = get_moment_feed(user_id, user_role)
    return 200, {"message": "Moment feed retrieved successfully", "moments": moments}


def get_moment_archive_controller(event):
    """Fetch archived moments and shape the HTTP response payload."""
    body = json.loads(event["body"])
    user_id = body.get("userId")
    user_role = "moderator"
    moments = get_moment_archive(user_id, user_role)
    return 200, {"message": "Moment archive retrieved successfully", "moments": moments}


def hide_moment_controller(event):
    """Hide a moment as moderator and shape the HTTP response payload."""
    body = json.loads(event["body"])
    moment_id = body.get("momentId")
    moderator_id = "babes idk yet, its a user id tho"
    moderator_role = "moderator"

    moment = hide_moment(moment_id, moderator_id, moderator_role)
    return 200, {"message": "Moment hidden successfully", "moment": moment}


def delete_moment_controller(moment_id: str, user_id: str, user_role: str) -> tuple[int, dict]:
    """Delete a moment and return success response payload."""
    body = json.loads(event["body"])
    moment_id = body.get("momentId")
    user_id = body.get("userId")
    user_role = "moderator"
    delete_moment(moment_id, user_id, user_role)
    return 200, {"message": "Moment deleted successfully"}

