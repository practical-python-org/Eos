"""
Route-level tests for the Flask API.

These ensure the response contract. Every endpoint returns a JSON *object*
carrying `status`, and the HTTP status code reflects that status.
"""

ROW = {"id": 1, "name": "Chat Log", "value": "123"}
ERROR = {"status": "error", "message": "Database error while doing a thing"}


def test_api_healthcheck_is_an_object(client):
    response = client().get("/hc_api")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_db_healthcheck_ok(client):
    response = client(database_health_check={"status": "ok"}).get("/hc_db")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_db_healthcheck_unhealthy_is_503(client):
    c = client(
        database_health_check={"status": "unhealthy", "message": "Database unreachable"}
    )
    response = c.get("/hc_db")

    assert response.status_code == 503
    assert response.get_json()["status"] == "unhealthy"


# --------------------------------------------------------------------------
# The three id/name/value resources share a structure, so they share these tests.
# (path, all-key, one-key, db method names)
# --------------------------------------------------------------------------
RESOURCES = [
    (
        "/logging",
        "log_settings",
        "log_setting",
        "get_log_settings",
        "get_log_setting",
        "update_logging",
    ),
    (
        "/settings",
        "settings",
        "setting",
        "get_settings",
        "get_setting",
        "update_setting",
    ),
    ("/role", "roles", "role", "get_roles", "get_role", "update_role"),
]


def test_get_all_returns_a_list_under_the_plural_key(client):
    for path, all_key, _, all_method, _, _ in RESOURCES:
        c = client(**{all_method: {"status": "ok", all_key: [ROW]}})
        response = c.get(path)

        assert response.status_code == 200, path
        body = response.get_json()
        assert isinstance(body, dict), f"{path} must return an object, not an array"
        assert body[all_key] == [ROW], path


def test_get_one_returns_a_dict_row_under_the_singular_key(client):
    for path, _, one_key, _, one_method, _ in RESOURCES:
        c = client(**{one_method: {"status": "ok", one_key: ROW}})
        response = c.get(f"{path}/1")

        assert response.status_code == 200, path
        assert response.get_json()[one_key] == ROW, path


def test_get_one_missing_row_is_404(client):
    for path, _, _, _, one_method, _ in RESOURCES:
        c = client(**{one_method: {"status": "not_found", "message": "nope"}})
        response = c.get(f"{path}/99")

        assert response.status_code == 404, path


def test_get_all_db_error_is_500(client):
    for path, _, _, all_method, _, _ in RESOURCES:
        response = client(**{all_method: ERROR}).get(path)

        assert response.status_code == 500, path


def test_update_passes_value_through(client):
    for path, _, _, _, _, update_method in RESOURCES:
        c = client(**{update_method: {"status": "ok", "message": "updated"}})
        response = c.put(f"{path}/1", json={"value": "999"})

        assert response.status_code == 200, path
        assert c.db.calls == [(update_method, (1, "999"), {})], path


def test_update_without_value_is_400(client):
    for path, _, _, _, _, update_method in RESOURCES:
        c = client(**{update_method: {"status": "ok"}})
        response = c.put(f"{path}/1", json={})

        assert response.status_code == 400, path
        assert c.db.calls == [], f"{path} must not reach the DB on a bad request"


def test_update_missing_row_is_404(client):
    for path, _, _, _, _, update_method in RESOURCES:
        c = client(**{update_method: {"status": "not_found", "message": "nope"}})
        response = c.put(f"{path}/99", json={"value": "1"})

        assert response.status_code == 404, path


# --------------------------------------------------------------------------
# Points
# --------------------------------------------------------------------------
def test_get_points_returns_a_scalar(client):
    c = client(get_points_for_user={"status": "ok", "points": 42})
    response = c.get("/points/123")

    assert response.status_code == 200
    assert response.get_json()["points"] == 42


def test_get_points_unknown_user_is_404(client):
    c = client(get_points_for_user={"status": "not_found", "message": "nope"})
    response = c.get("/points/123")

    assert response.status_code == 404


def test_get_monthly_points_returns_a_scalar(client):
    c = client(get_monthly_points_for_user={"status": "ok", "monthly_points": 7})
    response = c.get("/points/monthly/123")

    assert response.status_code == 200
    assert response.get_json()["monthly_points"] == 7


def test_update_points_accepts_an_integer(client):
    c = client(update_points={"status": "ok", "message": "Points updated successfully"})
    response = c.post("/points/123/update", json={"value": -5})

    assert response.status_code == 200
    assert c.db.calls == [("update_points", ("123", -5), {})]


def test_update_points_rejects_a_missing_value(client):
    c = client(update_points={"status": "ok"})
    response = c.post("/points/123/update", json={})

    assert response.status_code == 400
    assert c.db.calls == []


def test_update_points_rejects_a_non_integer_value(client):
    for bad in ("10", 1.5, True, None, [1]):
        c = client(update_points={"status": "ok"})
        response = c.post("/points/123/update", json={"value": bad})

        assert response.status_code == 400, bad
        assert c.db.calls == [], bad


def test_update_points_unknown_user_is_404(client):
    c = client(update_points={"status": "not_found", "message": "nope"})
    response = c.post("/points/123/update", json={"value": 1})

    assert response.status_code == 404


def test_add_user_is_201(client):
    c = client(add_user_to_points={"status": "ok", "message": "added"})
    response = c.post("/points/123/add")

    assert response.status_code == 201


def test_delete_user_is_200(client):
    c = client(remove_user_from_points={"status": "ok", "message": "deleted"})
    response = c.delete("/points/123")

    assert response.status_code == 200


def test_delete_unknown_user_is_404(client):
    c = client(remove_user_from_points={"status": "not_found", "message": "nope"})
    response = c.delete("/points/123")

    assert response.status_code == 404
    assert response.get_json()["status"] == "not_found"


def test_top10_returns_leaderboard_not_message(client):
    rows = [{"discord_id": "1", "points": 10}]
    c = client(get_top_10={"status": "ok", "leaderboard": rows})
    response = c.get("/points/top10")

    assert response.status_code == 200
    body = response.get_json()
    assert body["leaderboard"] == rows
    assert "message" not in body, "payloads must not travel under `message`"


def test_monthly_top10_returns_leaderboard(client):
    rows = [{"discord_id": "1", "monthly_points": 3}]
    c = client(get_monthly_top_10={"status": "ok", "leaderboard": rows})
    response = c.get("/points/monthly/top10")

    assert response.status_code == 200
    assert response.get_json()["leaderboard"] == rows


def test_monthly_top_earner(client):
    row = {"discord_id": "1", "monthly_points": 3}
    c = client(get_monthly_top_point_earner={"status": "ok", "top_earner": row})
    response = c.get("/points/monthly/top")

    assert response.status_code == 200
    assert response.get_json()["top_earner"] == row


def test_monthly_top_earner_with_no_users_is_404(client):
    c = client(get_monthly_top_point_earner={"status": "not_found", "message": "nope"})
    response = c.get("/points/monthly/top")

    assert response.status_code == 404


def test_reset_monthly_points(client):
    c = client(reset_monthly_points={"status": "ok", "message": "reset"})
    response = c.delete("/points/monthly/reset")

    assert response.status_code == 200


def test_static_point_routes_are_not_shadowed_by_the_user_id_route(client):
    """`/points/top10` must not be read as a user id of "top10"."""
    c = client(get_top_10={"status": "ok", "leaderboard": []})
    response = c.get("/points/top10")

    assert response.status_code == 200
    assert [call[0] for call in c.db.calls] == ["get_top_10"]


# --------------------------------------------------------------------------
# Parameters
# --------------------------------------------------------------------------
def test_get_parameter_returns_the_value(client):
    c = client(get_parameter={"status": "ok", "parameter": "42"})
    response = c.get("/parameters/monthly_yapper")

    assert response.status_code == 200
    assert response.get_json()["parameter"] == "42"


def test_get_unknown_parameter_is_404(client):
    c = client(get_parameter={"status": "not_found", "message": "nope"})
    response = c.get("/parameters/nope")

    assert response.status_code == 404


def test_set_parameter_takes_the_value_from_the_body(client):
    c = client(set_parameter={"status": "ok", "message": "set"})
    response = c.put("/parameters/monthly_yapper", json={"value": "a/b"})

    assert response.status_code == 200
    assert c.db.calls == [("set_parameter", ("monthly_yapper", "a/b"), {})]


def test_set_parameter_without_value_is_400(client):
    c = client(set_parameter={"status": "ok"})
    response = c.put("/parameters/monthly_yapper", json={})

    assert response.status_code == 400
    assert c.db.calls == []


# --------------------------------------------------------------------------
# Error handling
# --------------------------------------------------------------------------
def test_unknown_route_returns_the_envelope(client):
    response = client().get("/xarlos-is-a-god")

    assert response.status_code == 404
    assert response.get_json()["status"] == "error"


def test_wrong_method_returns_405(client):
    response = client().post("/hc_api")

    assert response.status_code == 405


def test_unhandled_exception_does_not_leak_the_message(client):
    class Boom:
        def get_roles(self):
            raise RuntimeError("password=d33znu7z")

        def __getattr__(self, name):
            raise AttributeError(name)

    app = client().application
    app.db = Boom()
    app.config["TESTING"] = False
    response = app.test_client().get("/role")

    assert response.status_code == 500
    body = response.get_json()
    assert body["status"] == "error"
    assert "d33znu7z" not in response.get_data(as_text=True)
