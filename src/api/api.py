import logging
import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from src.api.__logger__ import setup_logger
from src.api.core.db_helper import DB
from src.api.routes.healthchecks import health_checks
from src.api.routes.logging import logs
from src.api.routes.parameters import parameters
from src.api.routes.points import points
from src.api.routes.roles import role
from src.api.routes.settings import settings

logger = logging.getLogger(__name__)
setup_logger(
    level=int(os.getenv("API_LOG_LEVEL", "20")),
    stream_logs=os.getenv("STREAM_LOGS", "true").lower(),
)


app = Flask(__name__)
app.db = DB()

# API routes
app.register_blueprint(health_checks)
app.register_blueprint(logs)
app.register_blueprint(settings)
app.register_blueprint(points)
app.register_blueprint(role)
app.register_blueprint(parameters)


# Error handlers
@app.errorhandler(Exception)
def handle_exception(e):
    # Generic Application Errors
    app.logger.error(f"Unhandled exception: {str(e)}")

    # Return a JSON response with a generic error message
    return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500


@app.errorhandler(HTTPException)
def handle_http_exception(e):
    # HTTP Exception Errors
    app.logger.error(f"HTTP exception: {str(e)}")

    # Return a JSON response with details about the HTTP error
    return jsonify(
        {"error": str(e), "status_code": e.code, "description": e.description}
    ), e.code
