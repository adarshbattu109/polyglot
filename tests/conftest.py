"""Shared fixtures. No test reaches the network — the LLM call is always stubbed."""

import pytest
from fastapi.testclient import TestClient

from polyglot.app.main import app
from polyglot.helper import helper

SPANISH = {"text": "Hello", "target_languages": ["Spanish"]}
HOLA = {"language": "Spanish", "translation": "Hola"}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def app_routes():
    return {getattr(route, "path", None) for route in app.routes}


@pytest.fixture
def stub_llm(monkeypatch):
    """Swaps query_llm for a canned result and records the args it was called with.

    monkeypatch undoes the swap after each test, so a stubbed test cannot leak
    into one that exercises the real query_llm.
    """
    calls = []

    def install(result):
        def stub(host, port, payload, model, api_key, path):
            calls.append(
                {
                    "host": host,
                    "port": port,
                    "path": path,
                    "model": model,
                    "api_key": api_key,
                }
            )
            return result | {"id": payload["id"]}

        monkeypatch.setattr(helper, "query_llm", stub)
        return calls

    return install


@pytest.fixture
def spy_payload(monkeypatch):
    """Records the payload prepare_payload built, to assert on what the model was told."""
    seen = {}
    original = helper.prepare_payload

    def spy(*args, **kwargs):
        payload = original(*args, **kwargs)
        seen.update(payload)
        return payload

    monkeypatch.setattr(helper, "prepare_payload", spy)
    return seen
