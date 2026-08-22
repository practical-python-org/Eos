import logging

from flask import Blueprint, request
from flask import current_app as eos

from ._responses import respond

logger = logging.getLogger(__name__)

# Define a Blueprint
role = Blueprint("roles", __name__)


@role.route("/role", methods=["GET"])
@role.route("/role/<int:role_id>", methods=["GET"])
def get_role(role_id=None):
    """
    Grab roles from the database.

    :param role_id: optional ID of a specific role; all when None, and None for all!
    :return: JSON envelope with ``role`` or ``roles``
    """
    if role_id is None:
        return respond(eos.db.get_roles())

    return respond(eos.db.get_role(role_id))


@role.route("/role/<int:role_id>", methods=["PUT"])
def update_role(role_id):
    """
    Update an existing role in the database.
    """
    data = request.get_json(silent=True) or {}
    if "value" not in data:
        return {"status": "error", "message": "Missing required field: value"}, 400

    return respond(eos.db.update_role(role_id, data["value"]))
