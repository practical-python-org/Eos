import logging

from flask import Blueprint, request
from flask import current_app as eos

from ._responses import respond

logger = logging.getLogger(__name__)

# Define a Blueprint
points = Blueprint("points", __name__)


@points.route("/points/<user_id>", methods=["GET"])
def get_points(user_id):
    """
    Grab a user's points.
    """
    return respond(eos.db.get_points_for_user(user_id))


@points.route("/points/monthly/<user_id>", methods=["GET"])
def get_monthly_points(user_id):
    """
    Grab a user's points for the current month.
    """
    return respond(eos.db.get_monthly_points_for_user(user_id))


@points.route("/points/<user_id>/update", methods=["POST"])
def update_points(user_id):
    """
    Adjust a user's points by a signed amount.
    """
    data = request.get_json(silent=True) or {}
    if "value" not in data:
        return {"status": "error", "message": "Missing required field: value"}, 400

    value = data["value"]
    if isinstance(value, bool) or not isinstance(value, int):
        return {"status": "error", "message": "Field 'value' must be an integer"}, 400

    return respond(eos.db.update_points(user_id, value))


@points.route("/points/<user_id>/add", methods=["POST"])
def add_user_to_points(user_id):
    """
    Add a new user to the points table.
    """
    return respond(eos.db.add_user_to_points(user_id), w0o0o=201)


@points.route("/points/<user_id>", methods=["DELETE"])
def remove_user_from_points(user_id):
    """
    Remove a user from the points table.
    """
    return respond(eos.db.remove_user_from_points(user_id))


@points.route("/points/top10", methods=["GET"])
def top10():
    """
    The top 10 all-time point earners.
    """
    return respond(eos.db.get_top_10())


@points.route("/points/monthly/top", methods=["GET"])
def top_monthly():
    """
    The top point earner of the current month.
    """
    return respond(eos.db.get_monthly_top_point_earner())


@points.route("/points/monthly/top10", methods=["GET"])
def monthly_top10():
    """
    The top 10 point earners of the current month.
    """
    return respond(eos.db.get_monthly_top_10())


@points.route("/points/monthly/reset", methods=["DELETE"])
def reset_monthly_points():
    """
    Reset every member's monthly points to zero.
    """
    return respond(eos.db.reset_monthly_points())
