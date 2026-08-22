"""The two pre-flight endpoints: /verify (is this endpoint usable?) and /detect (what language?)."""

import pytest

from polyglot.constants.constants import API_KEY, HOST, MODEL, PATH, PORT
from tests.conftest import SPANISH


@pytest.fixture
def stub_verify(monkeypatch):
    """Swaps verify_connection and records the connection it was asked to check."""
    calls = []

    def install(result):
        def stub(host, port, model, api_key, path):
            calls.append(
                {
                    "host": host,
                    "port": port,
                    "path": path,
                    "model": model,
                    "api_key": api_key,
                }
            )
            return result

        monkeypatch.setattr("polyglot.app.main.verify_connection", stub)
        return calls

    return install


@pytest.fixture
def stub_detect(monkeypatch):
    """Swaps detect_language and records the text and connection it was given."""
    calls = []

    def install(result):
        def stub(text, host, port, model, api_key, path):
            calls.append(
                {"text": text, "host": host, "port": port, "path": path, "model": model}
            )
            return result

        monkeypatch.setattr("polyglot.app.main.detect_language", stub)
        return calls

    return install


# ── /verify ──────────────────────────────────────────────────────────────────


def test_verify_reports_a_usable_endpoint(client, stub_verify):
    stub_verify({"ok": True, "model_available": True, "models": ["gpt-oss:20b"]})
    response = client.post("/verify", json={"host": "ollama.com", "port": 443})

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_verify_passes_the_caller_connection_through(client, stub_verify):
    """The UI verifies the exact connection it is about to translate with, not the default."""
    calls = stub_verify({"ok": True, "model_available": True, "models": []})
    override = {
        "host": "api.x.ai",
        "port": 443,
        "path": "/v1",
        "model": "grok-4-fast",
        "api_key": "sk-x",
    }
    client.post("/verify", json=override)

    assert calls[0] == override


def test_verify_defaults_to_the_configured_connection(client, stub_verify):
    calls = stub_verify({"ok": True, "model_available": True, "models": []})
    client.post("/verify", json={})

    assert calls[0] == {
        "host": HOST,
        "port": PORT,
        "path": PATH,
        "model": MODEL,
        "api_key": API_KEY,
    }


def test_verify_is_502_when_the_endpoint_is_unreachable(client, stub_verify):
    """A failed check must be an HTTP failure, not a 200 with ok=false the UI might miss."""
    stub_verify({"ok": False, "error": "Connection refused", "models": []})
    response = client.post("/verify", json={"host": "localhost", "port": 9999})

    assert response.status_code == 502
    assert response.json()["error"] == "Connection refused"


def test_verify_502_still_carries_the_model_list(client, stub_verify):
    """A refused model with a working key: the UI shows the alternatives from this body."""
    stub_verify(
        {"ok": False, "error": "403 requires a subscription", "models": ["gpt-oss:20b"]}
    )
    response = client.post("/verify", json={"model": "premium:400b"})

    assert response.status_code == 502
    assert response.json()["models"] == ["gpt-oss:20b"]


def test_verify_is_200_when_connected_but_the_model_is_unlisted(client, stub_verify):
    """Connected-with-a-missing-model is a warning, not a failure — the model may be unlisted."""
    stub_verify({"ok": True, "model_available": False, "models": ["other"]})
    response = client.post("/verify", json={"model": "typo:1b"})

    assert response.status_code == 200
    assert response.json()["model_available"] is False


def test_verify_does_not_echo_the_key(client, stub_verify):
    stub_verify({"ok": True, "model_available": True, "models": []})
    response = client.post("/verify", json={"api_key": "sk-secret"})

    assert "sk-secret" not in response.text


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({"port": 0}, id="port-zero"),
        pytest.param({"port": 70000}, id="port-out-of-range"),
        pytest.param({"host": "  "}, id="blank-host"),
        pytest.param({"model": ""}, id="blank-model"),
    ],
)
def test_verify_rejects_an_unusable_connection(client, body):
    assert client.post("/verify", json=body).status_code == 422


# ── /detect ──────────────────────────────────────────────────────────────────


def test_detect_returns_a_language_and_confidence(client, stub_detect):
    stub_detect({"language": "Spanish", "confidence": "high"})
    response = client.post("/detect", json={"text": "Hola, ¿cómo estás?"})

    assert response.status_code == 200
    assert response.json() == {"language": "Spanish", "confidence": "high"}


def test_detect_uses_the_caller_connection(client, stub_detect):
    """Detection runs against the endpoint the user just verified, not the default one."""
    calls = stub_detect({"language": "Spanish", "confidence": "high"})
    client.post(
        "/detect",
        json={"text": "Hola", "host": "api.x.ai", "port": 443, "model": "grok-4-fast"},
    )

    assert calls[0]["host"] == "api.x.ai"
    assert calls[0]["model"] == "grok-4-fast"


def test_detect_failure_is_502(client, stub_detect):
    """Detection is optional, so a failure must be visible without blocking translation."""
    stub_detect({"error": "Connection refused"})
    response = client.post("/detect", json={"text": "Hola"})

    assert response.status_code == 502
    assert response.json()["error"] == "Connection refused"


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="no-text"),
        pytest.param({"text": ""}, id="blank-text"),
        pytest.param({"text": "   "}, id="whitespace-text"),
    ],
)
def test_detect_rejects_empty_text(client, body):
    """There is nothing to identify, so this must not cost an inference."""
    assert client.post("/detect", json=body).status_code == 422


def test_both_endpoints_are_mounted(app_routes):
    assert {"/verify", "/detect"} <= app_routes
    # /translate must not have been displaced by the new pre-flight routes
    assert "/translate" in app_routes


def test_detect_ignores_the_translate_body_shape(client, stub_detect):
    """SPANISH carries target_languages; /detect must ignore extras, not 422 on them."""
    stub_detect({"language": "English", "confidence": "high"})

    assert client.post("/detect", json=SPANISH).status_code == 200
