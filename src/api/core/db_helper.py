import logging
import os
from contextlib import contextmanager

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

# serversettings, logging and roles are structurally identical
# (id SERIAL, name VARCHAR, value VARCHAR), so they share one set of helpers.
SETTINGS_TABLE = "serversettings"
LOGGING_TABLE = "logging"
ROLES_TABLE = "roles"
_KEY_VALUE_TABLES = frozenset({SETTINGS_TABLE, LOGGING_TABLE, ROLES_TABLE})

# Seconds to wait for a pooled connection before giving up.
POOL_TIMEOUT = 5.0


def _build_pool() -> ConnectionPool:
    """
    Build the connection pool.
    Let's go swimming!
    """
    pool = ConnectionPool(
        kwargs={
            "dbname": os.getenv("POSTGRES_DB"),
            "user": os.getenv("POSTGRES_USER"),
            "password": os.getenv("POSTGRES_PASSWORD"),
            "host": os.getenv("POSTGRES_HOST"),
            "port": os.getenv("POSTGRES_PORT", "5432"),
            "autocommit": True,
            "row_factory": dict_row,
        },
        min_size=1,
        max_size=4,
        check=ConnectionPool.check_connection,
        name="eos-api",
        open=False,
    )
    pool.open()
    return pool


class DB:
    """
    All database access for the API.
    """

    def __init__(self, pool: ConnectionPool | None = None):
        self.pool = pool if pool is not None else _build_pool()

    @contextmanager
    def _cursor(self):
        with self.pool.connection(timeout=POOL_TIMEOUT) as conn, conn.cursor() as cur:
            yield cur

    @staticmethod
    def _error(action: str, err: Exception) -> dict:
        logger.error("Error %s: %s", action, err)
        return {"status": "error", "message": f"Database error while {action}"}

    @staticmethod
    def _check_table(table: str) -> None:
        if table not in _KEY_VALUE_TABLES:
            raise ValueError(f"Unknown table: {table}")

    ##################
    ## Healthchecks ##
    ##################
    def database_health_check(self):
        logger.debug("API attempting to contact DB for healthcheck...")
        try:
            with self._cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return {"status": "ok"}
        except (psycopg.Error, OSError) as err:
            logger.critical("DB healthcheck failed: %s", err)
            return {"status": "unhealthy", "message": "Database unreachable"}

    ############################
    ## Shared id/name/value  ##
    ############################
    def _get_row(self, table: str, row_id, key: str) -> dict:
        self._check_table(table)
        try:
            with self._cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT id, name, value FROM {} WHERE id = %s").format(
                        sql.Identifier(table)
                    ),
                    (row_id,),
                )
                row = cur.fetchone()
        except psycopg.Error as err:
            return self._error(f"fetching {table} row {row_id}", err)

        if row is None:
            return {
                "status": "not_found",
                "message": f"No {table} row with ID {row_id}",
            }
        return {"status": "ok", key: row}

    def _get_rows(self, table: str, key: str) -> dict:
        self._check_table(table)
        try:
            with self._cursor() as cur:
                cur.execute(
                    sql.SQL("SELECT id, name, value FROM {} ORDER BY id").format(
                        sql.Identifier(table)
                    )
                )
                rows = cur.fetchall()
        except psycopg.Error as err:
            return self._error(f"fetching {table}", err)

        return {"status": "ok", key: rows}

    def _update_row(self, table: str, row_id, value) -> dict:
        self._check_table(table)
        logger.debug("Updating %s row %s to %s", table, row_id, value)
        try:
            with self._cursor() as cur:
                cur.execute(
                    sql.SQL("UPDATE {} SET value = %s WHERE id = %s").format(
                        sql.Identifier(table)
                    ),
                    (value, row_id),
                )
                updated = cur.rowcount
        except psycopg.Error as err:
            return self._error(f"updating {table} row {row_id}", err)

        if not updated:
            return {
                "status": "not_found",
                "message": f"No {table} row with ID {row_id}",
            }
        return {"status": "ok", "message": f"{table} row {row_id} updated successfully"}

    ###############
    ##  Logging  ##
    ###############
    def get_log_setting(self, log_id):
        return self._get_row(LOGGING_TABLE, log_id, "log_setting")

    def get_log_settings(self):
        return self._get_rows(LOGGING_TABLE, "log_settings")

    def update_logging(self, log_id, value):
        return self._update_row(LOGGING_TABLE, log_id, value)

    ################
    ##  Settings  ##
    ################
    def get_setting(self, setting_id):
        return self._get_row(SETTINGS_TABLE, setting_id, "setting")

    def get_settings(self):
        return self._get_rows(SETTINGS_TABLE, "settings")

    def update_setting(self, setting_id, value):
        return self._update_row(SETTINGS_TABLE, setting_id, value)

    #############
    ##  Roles  ##
    #############
    def get_role(self, role_id):
        return self._get_row(ROLES_TABLE, role_id, "role")

    def get_roles(self):
        return self._get_rows(ROLES_TABLE, "roles")

    def update_role(self, role_id, value):
        return self._update_row(ROLES_TABLE, role_id, value)

    ##############
    ##  Points  ##
    ##############
    def get_points_for_user(self, user_id):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT points FROM users WHERE discord_id = %s", (user_id,)
                )
                row = cur.fetchone()
        except psycopg.Error as err:
            return self._error(f"fetching points for user {user_id}", err)

        if row is None:
            return {"status": "not_found", "message": f"No user with ID {user_id}"}
        return {"status": "ok", "points": row["points"]}

    def get_monthly_points_for_user(self, user_id):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT monthly_points FROM users WHERE discord_id = %s", (user_id,)
                )
                row = cur.fetchone()
        except psycopg.Error as err:
            return self._error(f"fetching monthly points for user {user_id}", err)

        if row is None:
            return {"status": "not_found", "message": f"No user with ID {user_id}"}
        return {"status": "ok", "monthly_points": row["monthly_points"]}

    def update_points(self, user_id, value):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE users SET points = points + %s, "
                    "monthly_points = monthly_points + %s WHERE discord_id = %s",
                    (value, value, user_id),
                )
                updated = cur.rowcount
        except psycopg.Error as err:
            return self._error(f"updating points for user {user_id}", err)

        if not updated:
            return {"status": "not_found", "message": f"No user with ID {user_id}"}
        return {"status": "ok", "message": "Points updated successfully"}

    def add_user_to_points(self, user_id):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "INSERT INTO users (discord_id, points, monthly_points) "
                    "VALUES (%s, 0, 0) ON CONFLICT (discord_id) DO NOTHING",
                    (user_id,),
                )
        except psycopg.Error as err:
            return self._error(f"adding user {user_id}", err)

        return {"status": "ok", "message": f"User {user_id} added successfully"}

    def remove_user_from_points(self, user_id):
        try:
            with self._cursor() as cur:
                cur.execute("DELETE FROM users WHERE discord_id = %s", (user_id,))
                deleted = cur.rowcount
        except psycopg.Error as err:
            return self._error(f"deleting user {user_id}", err)

        if not deleted:
            return {"status": "not_found", "message": f"No user with ID {user_id}"}
        return {"status": "ok", "message": f"User {user_id} deleted successfully"}

    def get_top_10(self):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT discord_id, points FROM users ORDER BY points DESC LIMIT 10"
                )
                rows = cur.fetchall()
        except psycopg.Error as err:
            return self._error("fetching the points leaderboard", err)

        return {"status": "ok", "leaderboard": rows}

    def get_monthly_top_10(self):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT discord_id, monthly_points FROM users "
                    "ORDER BY monthly_points DESC LIMIT 10"
                )
                rows = cur.fetchall()
        except psycopg.Error as err:
            return self._error("fetching the monthly points leaderboard", err)

        return {"status": "ok", "leaderboard": rows}

    def get_monthly_top_point_earner(self):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT discord_id, monthly_points FROM users "
                    "ORDER BY monthly_points DESC LIMIT 1"
                )
                row = cur.fetchone()
        except psycopg.Error as err:
            return self._error("fetching the monthly top point earner", err)

        if row is None:
            return {"status": "not_found", "message": "No users with points recorded"}
        return {"status": "ok", "top_earner": row}

    def reset_monthly_points(self):
        try:
            with self._cursor() as cur:
                cur.execute("UPDATE users SET monthly_points = 0")
        except psycopg.Error as err:
            return self._error("resetting monthly points", err)

        return {"status": "ok", "message": "Monthly points reset successfully"}

    ##################
    ##  Parameters  ##
    ##################
    def get_parameter(self, parameter_name):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "SELECT parameter_value FROM parameters WHERE parameter_name = %s",
                    (parameter_name,),
                )
                row = cur.fetchone()
        except psycopg.Error as err:
            return self._error(f"fetching parameter {parameter_name}", err)

        if row is None:
            return {
                "status": "not_found",
                "message": f"No parameter named {parameter_name}",
            }
        return {"status": "ok", "parameter": row["parameter_value"]}

    def set_parameter(self, parameter_name, parameter_value):
        try:
            with self._cursor() as cur:
                cur.execute(
                    "UPDATE parameters SET parameter_value = %s "
                    "WHERE parameter_name = %s",
                    (parameter_value, parameter_name),
                )
                updated = cur.rowcount
        except psycopg.Error as err:
            return self._error(f"setting parameter {parameter_name}", err)

        if not updated:
            return {
                "status": "not_found",
                "message": f"No parameter named {parameter_name}",
            }
        return {"status": "ok", "message": f"Parameter {parameter_name} set"}
