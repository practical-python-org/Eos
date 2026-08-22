import logging

from flask import Blueprint, request
from flask import current_app as eos

from ._responses import respond

logger = logging.getLogger(__name__)

# Define a Blueprint
settings = Blueprint("settings", __name__)


@settings.route("/settings", methods=["GET"])
@settings.route("/settings/<int:setting_id>", methods=["GET"])
def get_setting(setting_id=None):
    """
    Grab settings from the database.

    :param setting_id: optional ID of a specific setting; all when omitted
    :return: JSON envelope with ``setting`` or ``settings``
    """
    if setting_id is None:
        return respond(eos.db.get_settings())

    return respond(eos.db.get_setting(setting_id))


@settings.route("/settings/<int:setting_id>", methods=["PUT"])
def update_setting(setting_id):
    """
    Update an existing setting in the database.
    """
    data = request.get_json(silent=True) or {}
    if "value" not in data:
        return {"status": "error", "message": "Missing required field: value"}, 400

    return respond(eos.db.update_setting(setting_id, data["value"]))
