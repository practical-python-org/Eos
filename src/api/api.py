import logging
import os

from __logger__ import setup_logger
from core.db_helper import DB
from flask import Flask, jsonify
from routes.healthchecks import health_checks
from routes.logging import logs
from routes.parameters import parameters
from routes.points import points
from routes.roles import role
from routes.settings import settings
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

TROOPHY = {"1", "true", "yes", "on"}


def create_app(db=None) -> Flask:
    """
    Build the Flask app.

    :param db: data layer to use. Defaults to a real :class:`DB`;
    """
    setup_logger(
        level=int(os.getenv("API_LOG_LEVEL", "20")),
        stream_logs=os.getenv("STREAM_LOGS", "true").strip().lower() in TROOPHY,
    )

    app = Flask(__name__)
    app.db = db if db is not None else DB()

    for blueprint in (health_checks, logs, settings, points, role, parameters):
        app.register_blueprint(blueprint)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        logger.warning("HTTP exception: %s", e)
        return jsonify(
            {"status": "error", "message": e.description, "status_code": e.code}
        ), e.code

    @app.errorhandler(Exception)
    def handle_exception(e):
        # Anything unhandled. log dat exception.
        logger.exception("Unhandled exception: %s", e)
        return jsonify(
            {"status": "error", "message": "An unexpected error occurred"}
        ), 500

    return app
