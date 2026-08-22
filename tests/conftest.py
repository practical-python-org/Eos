import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "src" / "api"

_CLASHING = ("core", "routes", "api", "__logger__")


def _is_clashing(name: str) -> bool:
    return name.split(".")[0] in _CLASHING


def _purge() -> dict:
    return {
        name: sys.modules.pop(name) for name in list(sys.modules) if _is_clashing(name)
    }


def _restore(saved: dict) -> None:
    for name in list(sys.modules):
        if _is_clashing(name):
            del sys.modules[name]
    sys.modules.update(saved)


@pytest.fixture(scope="session")
def create_app():
    """imported without breaking the bot's `core` app."""
    saved_path = list(sys.path)
    saved_modules = _purge()
    sys.path.insert(0, str(API_SRC))
    try:
        from api import create_app as factory
    finally:
        sys.path[:] = saved_path
        _restore(saved_modules)
    return factory


class FakeDB:
    """
    Stand-in for core.db_helper.DB.

    Every method returns whatever was queued for it under the same name, so a
    test can slam any response through the routes without a database.
    """

    def __init__(self, **results):
        self.results = results
        self.calls = []

    def __getattr__(self, name):
        def method(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            try:
                return self.results[name]
            except KeyError:
                raise AssertionError(
                    f"FakeDB got an unexpected call to {name}()"
                ) from None

        return method


@pytest.fixture
def client(create_app):
    """Build a test client against a FakeDB configured per-test."""

    def _build(**results):
        db = FakeDB(**results)
        app = create_app(db=db)
        app.config.update(TESTING=True)
        test_client = app.test_client()
        test_client.db = db
        return test_client

    return _build
