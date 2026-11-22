import logging
import os

from nicegui import app, ui

from src.ui.__logger__ import setup_logger
from src.ui.core.api_client import API

logger = logging.getLogger(__name__)

TROOPHY = {"1", "true", "yes", "on"}

setup_logger(
    level=int(os.getenv("UI_LOG_LEVEL", "20")),
    stream_logs=os.getenv("STREAM_LOGS", "true").strip().lower() in TROOPHY,
)

api = API()


@app.get("/hc_ui")
def health_check():
    """get health, noob."""
    return {"status": "ok", "message": "UI is alive"}


def _save(container, setting_id, name, field) -> None:
    """Update a setting via the API, then re-read so the page shows the DB."""
    result = api.update_setting(setting_id, field.value)
    if result.get("status") != "ok":
        logger.error("Failed to update setting %s: %s", setting_id, result)
        ui.notify(f"Failed to save {name}: {result.get('message')}", type="negative")
    else:
        logger.info("Updated setting %s (%s)", setting_id, name)
        ui.notify(f"Saved {name}", type="positive")

    # Always redraw from the API — never leave a typed (or rejected) value on
    # screen pretending to be what the database holds.
    _render_settings(container)


def _render_settings(container) -> None:
    """Hit the API, and dump out what we have inside of it"""
    container.clear()

    result = api.get_settings()
    with container:
        if result.get("status") != "ok":
            logger.error("Failed to load settings: %s", result)
            ui.label(f"Could not load settings: {result.get('message')}").classes(
                "text-red-600"
            )
            return

        for setting in result.get("settings", []):
            with ui.row().classes("w-full items-center gap-4"):
                ui.label(setting["name"]).classes("w-64")
                field = ui.input(value=setting["value"] or "").classes("w-64")
                ui.button(
                    "Save",
                    on_click=lambda _, s=setting, f=field: _save(
                        container, s["id"], s["name"], f
                    ),
                )


@ui.page("/")
def index():
    """server settings"""
    ui.label("Eos Admin — Server Settings").classes("text-2xl font-bold")

    health = api.health_check()
    ui.label(f"API: {health.get('status')}").classes("text-sm text-gray-500")

    ui.button("Refresh", on_click=lambda: _render_settings(container))
    container = ui.column().classes("w-full gap-2")
    _render_settings(container)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        host="0.0.0.0",  # noqa: S104  # nosec B104
        port=int(os.getenv("UI_PORT", "8080")),
        title="Eos Admin",
        reload=False,
        show=False,
    )
