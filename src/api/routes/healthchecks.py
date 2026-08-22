import logging

from flask import Blueprint, jsonify
from flask import current_app as eos

from ._responses import respond

logger = logging.getLogger(__name__)

# Define a Blueprint
health_checks = Blueprint("health_checks", __name__)


@health_checks.route("/hc_api", methods=["GET"])
def api_health_check():
    """
    A simple healthcheck that returns an up status.
    """
    return jsonify({"status": "ok"}), 200


@health_checks.route("/hc_db", methods=["GET"])
def database_health_check():
    """
    A simple healthcheck that returns an up status.
    """
    return respond(eos.db.database_health_check())
