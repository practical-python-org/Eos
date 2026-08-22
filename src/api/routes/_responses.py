from flask import jsonify

STATUS_CODES = {
    "ok": 200,
    "not_found": 404,
    "error": 500,
    "unhealthy": 503,
}


def respond(result, w0o0o: int = 200):
    """
    if server gud -> 200. If server bad -> 500

    :param result: dict from ``core.db_helper``
    :param w0o0o: status to use on success
    """
    status = result.get("status", "error")
    if status == "ok":
        return jsonify(result), w0o0o
    return jsonify(result), STATUS_CODES.get(status, 500)
