"""The /translate contract: what a browser may send and what it gets back."""

import pytest

from polyglot.constants.constants import API_KEY, HOST, MODEL, PATH, PORT, PROVIDERS
from tests.conftest import HOLA, SPANISH


def test_text_and_languages_are_enough(client, stub_llm):
    """Connection fields are optional; omitting them uses the configured defaults."""
    calls = stub_llm({"text": "Hello", "translations": [HOLA]})
    response = client.post("/translate", json=SPANISH)

    assert response.status_code == 200
    body = response.json()
    assert body["translations"] == [HOLA]
    assert body["id"].startswith("polyglot_")
    assert calls[0] == {
        "host": HOST,
        "port": PORT,
        "path": PATH,
        "model": MODEL,
        "api_key": API_KEY,
    }


def test_connection_fields_override_the_defaults(client, stub_llm):
    """The UI needs to aim the server at an arbitrary OpenAI-compatible endpoint."""
    calls = stub_llm({"text": "Hi", "translations": [HOLA]})
    override = {
        "host": "10.0.0.7",
        "port": 443,
        # Gemini serves its OpenAI surface off /v1, so the path has to travel too
        "path": "/v1beta/openai",
        "model": "llama3",
        "api_key": "sk-x",
    }
    response = client.post("/translate", json=SPANISH | override)

    assert response.status_code == 200
    assert calls[0] == override


def test_partial_override_leaves_the_rest_at_defaults(client, stub_llm):
    """A UI that fills only Host must not blank out model or key."""
    calls = stub_llm({"text": "Hi", "translations": [HOLA]})
    client.post("/translate", json=SPANISH | {"host": "10.0.0.7"})

    assert calls[0] == {
        "host": "10.0.0.7",
        "port": PORT,
        "path": PATH,
        "model": MODEL,
        "api_key": API_KEY,
    }


def test_api_key_is_not_echoed_back(client, stub_llm):
    """The key goes out with the request; it must not come back in the response body."""
    stub_llm({"text": "Hi", "translations": [HOLA]})
    response = client.post("/translate", json=SPANISH | {"api_key": "sk-secret"})

    assert "sk-secret" not in response.text


def test_config_exposes_defaults_without_the_key(client):
    """The UI prefills from this, so it must carry the endpoint but never the credential."""
    body = client.get("/config").json()

    assert body["host"] == HOST
    assert body["port"] == PORT
    assert body["model"] == MODEL
    assert "api_key" not in body


def test_config_ships_the_provider_presets(client):
    """The UI builds its provider menu from this, so the shape it reads must be present."""
    providers = client.get("/config").json()["providers"]

    assert providers == PROVIDERS
    assert {"id", "label", "host", "port", "model", "needs_key"} <= set(providers[0])
    # Custom is what the UI falls back to for a hand-configured endpoint
    assert any(p["id"] == "custom" for p in providers)


def test_no_preset_carries_a_key(client):
    """Presets are shipped to every browser that loads the page; a key in one would leak."""
    assert not any(
        "api_key" in p or "key" in p for p in client.get("/config").json()["providers"]
    )


def test_source_language_reaches_the_model(client, stub_llm, spy_payload):
    """A corrected language has to arrive in the payload, or correcting it does nothing."""
    stub_llm({"text": "Hola", "translations": [HOLA]})
    client.post("/translate", json=SPANISH | {"source_language": "Catalan"})

    assert spy_payload["source_language"] == "Catalan"


def test_source_language_defaults_to_blank_for_the_model_to_decide(
    client, stub_llm, spy_payload
):
    stub_llm({"text": "Hello", "translations": [HOLA]})
    client.post("/translate", json=SPANISH)

    assert spy_payload["source_language"] == ""


@pytest.mark.parametrize(
    "body",
    [
        pytest.param({}, id="empty"),
        pytest.param({"text": "Hello"}, id="no-languages-key"),
        pytest.param({**SPANISH, "text": ""}, id="blank-text"),
        pytest.param({**SPANISH, "text": "   "}, id="whitespace-text"),
        pytest.param({**SPANISH, "target_languages": []}, id="no-languages"),
        pytest.param({**SPANISH, "target_languages": ["  "]}, id="blank-language"),
        pytest.param({**SPANISH, "port": 0}, id="port-zero"),
        pytest.param({**SPANISH, "port": 70000}, id="port-out-of-range"),
        pytest.param({**SPANISH, "port": "http"}, id="port-not-a-number"),
        pytest.param({**SPANISH, "host": "  "}, id="blank-host"),
        pytest.param({**SPANISH, "model": ""}, id="blank-model"),
    ],
)
def test_invalid_input_is_rejected_not_answered(client, body):
    """Every one of these used to return 200 with an error body."""
    assert client.post("/translate", json=body).status_code == 422


def test_upstream_failure_is_502_with_the_error_intact(client, stub_llm):
    stub_llm({"text": "Hello", "translations": [], "error": "Connection refused"})
    response = client.post("/translate", json=SPANISH)

    assert response.status_code == 502
    assert response.json()["error"] == "Connection refused"


def test_non_json_model_output_keeps_its_raw_marker(client, stub_llm):
    """The UI relies on raw_response to label unstructured output as not-a-translation."""
    raw = {"language": "response", "translation": "sure!"}
    stub_llm({"text": "Hello", "translations": [raw], "raw_response": "sure!"})
    response = client.post("/translate", json=SPANISH)

    assert response.status_code == 200
    assert response.json()["raw_response"] == "sure!"
