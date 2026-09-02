import pytest
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    # Enter the client as a context manager so ALL websocket sessions share one event loop (portal).
    # Without this, Starlette gives every websocket_connect() its own loop and a broadcast from the
    # edge socket can never wake the viewer socket → the ingest test hangs forever.
    with TestClient(app) as c:
        yield c
