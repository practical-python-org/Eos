import logging

from flask import Blueprint, request
from flask import current_app as eos

from ._responses import respond

logger = logging.getLogger(__name__)

# Define a Blueprint
parameters = Blueprint("parameters", __name__)


@parameters.route("/parameters/<parameter_name>", methods=["GET"])
def get_parameter(parameter_name):
    """
    Grab the value of a parameter from the DB.
    """
    return respond(eos.db.get_parameter(parameter_name))


@parameters.route("/parameters/<parameter_name>", methods=["PUT"])
def set_parameter(parameter_name):
    """
    Set the value of a parameter in the DB.

    The value is taken from the JSON body rather than the URL path
    """
    data = request.get_json(silent=True) or {}
    if "value" not in data:
        return {"status": "error", "message": "Missing required field: value"}, 400

    return respond(eos.db.set_parameter(parameter_name, data["value"]))
