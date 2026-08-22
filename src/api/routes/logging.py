import logging

from flask import Blueprint, request
from flask import current_app as eos

from ._responses import respond

logger = logging.getLogger(__name__)

# Define a Blueprint
logs = Blueprint("logging", __name__)


@logs.route("/logging", methods=["GET"])
@logs.route("/logging/<int:log_id>", methods=["GET"])
def get_log_setting(log_id=None):
    """
    Grab logging settings from the database.

    :param log_id: optional ID of a specific log setting; all when None, and one for all!
    :return: JSON envelope with ``log_setting`` or ``log_settings``
    """
    if log_id is None:
        return respond(eos.db.get_log_settings())

    return respond(eos.db.get_log_setting(log_id))


@logs.route("/logging/<int:log_id>", methods=["PUT"])
def update_log_setting(log_id):
    """
    Update an existing log setting in the database.
    """
    data = request.get_json(silent=True) or {}
    if "value" not in data:
        return {"status": "error", "message": "Missing required field: value"}, 400

    return respond(eos.db.update_logging(log_id, data["value"]))
