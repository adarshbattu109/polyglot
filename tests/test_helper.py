"""Response parsing and failure shaping for query_llm, verify_connection and detect_language."""

import pytest

from polyglot.helper.helper import (
    base_url,
    detect_language,
    prepare_payload,
    query_llm,
    translate_batch,
    verify_connection,
)

PAYLOAD = {"id": "polyglot_0001", "text": "Hello", "target_languages": ["Spanish"]}


class FakeOpenAI:
    """Stands in for the OpenAI client. `content` of None mimics a model returning nothing.

    `models` doubles as the models.list() result; a `raises` instance mimics an endpoint that
    cannot be reached at all.
    """

    def __init__(
        self,
        content="",
        choices=True,
        models=(),
        raises=None,
        list_raises=None,
        create_raises=None,
        usage=None,
        **kwargs,
    ):
        self._content = content
        self._choices = choices
        self._models = models
        # `raises` fails both calls, as an unreachable server does. The narrower two fail one
        # each: a server with no /v1/models, or a key/model the completion endpoint refuses.
        self._list_raises = list_raises or raises
        self._create_raises = create_raises or raises
        self._usage = usage
        self.chat = self

    @property
    def completions(self):
        return self

    @property
    def models(self):
        return self

    def list(self):
        if self._list_raises:
            raise self._list_raises
        data = [type("Model", (), {"id": name}) for name in self._models]
        return type("ModelList", (), {"data": data})

    def create(self, **kwargs):
        if self._create_raises:
            raise self._create_raises
        message = type("Message", (), {"content": self._content})
        choice = type("Choice", (), {"message": message})
        usage = None
        if self._usage is not None:
            usage = type(
                "Usage",
                (),
                {
                    "prompt_tokens": self._usage.get("prompt_tokens"),
                    "completion_tokens": self._usage.get("completion_tokens"),
                    "total_tokens": self._usage.get("total_tokens"),
                },
            )()
        return type(
            "Response",
            (),
            {
                "choices": [choice] if self._choices else [],
                "usage": usage,
            },
        )()


def install(monkeypatch, **kwargs):
    monkeypatch.setattr(
        "polyglot.helper.helper.OpenAI", lambda **_: FakeOpenAI(**kwargs)
    )


def test_json_response_is_parsed(monkeypatch):
    install(monkeypatch, content='{"id": "polyglot_0001", "translations": []}')
    assert query_llm("localhost", 11434, PAYLOAD)["id"] == "polyglot_0001"


def test_non_json_response_falls_back_to_raw(monkeypatch):
    install(monkeypatch, content="Hola!")
    result = query_llm("localhost", 11434, PAYLOAD)

    assert result["raw_response"] == "Hola!"
    assert result["translations"] == [{"language": "response", "translation": "Hola!"}]


def test_content_of_none_does_not_raise_typeerror(monkeypatch):
    """json.loads(None) raises TypeError, which used to escape the JSONDecodeError handler."""
    install(monkeypatch, content=None)
    result = query_llm("localhost", 11434, PAYLOAD)

    assert result["error"] == "LLM returned an empty response."
    assert result["translations"] == []


def test_empty_choices_does_not_raise_indexerror(monkeypatch):
    install(monkeypatch, choices=False)
    result = query_llm("localhost", 11434, PAYLOAD)

    assert result["error"] == "LLM returned an empty response."
    assert result["translations"] == []


def test_failure_echoes_the_request_id_and_text(monkeypatch):
    """The client needs to correlate a failure with the request that caused it."""
    install(monkeypatch, choices=False)
    result = query_llm("localhost", 11434, PAYLOAD)

    assert result["id"] == PAYLOAD["id"]
    assert result["text"] == PAYLOAD["text"]


def test_payload_carries_the_source_language(monkeypatch):
    """The prompt reads source_language, so the key must be present even when blank."""
    monkeypatch.setattr("polyglot.helper.helper.generate_id", lambda: "polyglot_0001")

    assert (
        prepare_payload("Hola", ["English"], "Spanish")["source_language"] == "Spanish"
    )
    assert prepare_payload("Hola", ["English"])["source_language"] == ""


# ── base_url ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("host", "port", "path", "expected"),
    [
        pytest.param(
            "localhost", 11434, "/v1", "http://localhost:11434/v1", id="local-http"
        ),
        pytest.param("ollama.com", 443, "/v1", "https://ollama.com:443/v1", id="tls"),
        pytest.param(
            "generativelanguage.googleapis.com",
            443,
            "/v1beta/openai",
            "https://generativelanguage.googleapis.com:443/v1beta/openai",
            id="gemini-nested-path",
        ),
        pytest.param(
            "api.groq.com",
            443,
            "/openai/v1",
            "https://api.groq.com:443/openai/v1",
            id="groq-prefixed-path",
        ),
        # a path pasted with or without slashes must not produce a doubled or missing one
        pytest.param("h", 80, "v1", "http://h:80/v1", id="no-leading-slash"),
        pytest.param("h", 80, "/v1/", "http://h:80/v1", id="trailing-slash"),
    ],
)
def test_base_url_builds_the_endpoint(host, port, path, expected):
    """Only 443 is HTTPS, and the base path is whatever the provider serves under."""
    assert base_url(host, port, path) == expected


def test_gemini_path_reaches_the_client(monkeypatch):
    """A provider's base path is useless if it stops at the helper's signature."""
    seen = {}

    def capture(**kwargs):
        seen.update(kwargs)
        return FakeOpenAI(content='{"translations": []}')

    monkeypatch.setattr("polyglot.helper.helper.OpenAI", capture)
    query_llm("generativelanguage.googleapis.com", 443, PAYLOAD, path="/v1beta/openai")

    assert seen["base_url"] == (
        "https://generativelanguage.googleapis.com:443/v1beta/openai"
    )


# ── verify_connection ────────────────────────────────────────────────────────


def test_verify_lists_the_models_it_can_see(monkeypatch):
    install(monkeypatch, models=["gpt-oss:120b", "gpt-oss:20b"])
    result = verify_connection("ollama.com", 443, "gpt-oss:20b")

    assert result["ok"] is True
    assert result["model_available"] is True
    # sorted, because the UI shows the list as-is
    assert result["models"] == ["gpt-oss:120b", "gpt-oss:20b"]


def test_verify_flags_a_model_the_endpoint_did_not_list(monkeypatch):
    """It still answered, so it is usable — the flag is a warning, not a failure."""
    install(monkeypatch, models=["gpt-oss:120b"])
    result = verify_connection("ollama.com", 443, "typo:1b")

    assert result["ok"] is True
    assert result["model_available"] is False


def test_verify_reports_an_unreachable_endpoint_as_not_ok(monkeypatch):
    """An unusable endpoint must be a clean verdict, not an exception out of the endpoint."""
    install(monkeypatch, raises=ConnectionError("Connection refused"))
    result = verify_connection("localhost", 9999)

    assert result == {"ok": False, "error": "Connection refused", "models": []}


def test_verify_accepts_an_endpoint_with_no_models_listed(monkeypatch):
    """Some servers don't implement /v1/models; the completion is what decides."""
    install(monkeypatch, models=[])
    result = verify_connection("localhost", 11434, "gpt-oss:20b")

    assert result["ok"] is True
    assert result["models"] == []
    # nothing to contradict, so don't warn about a model the server never advertised
    assert result["model_available"] is True


def test_verify_rejects_a_bad_key_that_the_listing_still_answers(monkeypatch):
    """Ollama serves /v1/models to an invalid key, so listing alone must not mean "verified"."""
    monkeypatch.setattr(
        "polyglot.helper.helper.OpenAI",
        lambda **_: FakeOpenAI(
            models=["gpt-oss:20b"], create_raises=PermissionError("401 invalid api key")
        ),
    )
    result = verify_connection("ollama.com", 443, "gpt-oss:20b")

    assert result["ok"] is False
    assert "401" in result["error"]


def test_verify_returns_the_listing_even_when_the_model_is_refused(monkeypatch):
    """The UI offers these as alternatives, so a refusal must not discard them."""
    monkeypatch.setattr(
        "polyglot.helper.helper.OpenAI",
        lambda **_: FakeOpenAI(
            models=["gpt-oss:20b"],
            create_raises=PermissionError("403 this model requires a subscription"),
        ),
    )
    result = verify_connection("ollama.com", 443, "premium:400b")

    assert result["ok"] is False
    assert result["models"] == ["gpt-oss:20b"]


def test_verify_survives_an_endpoint_that_refuses_to_list(monkeypatch):
    """A 404 on /v1/models must not sink an endpoint whose completions work fine."""
    monkeypatch.setattr(
        "polyglot.helper.helper.OpenAI",
        lambda **_: FakeOpenAI(list_raises=RuntimeError("404 page not found")),
    )
    result = verify_connection("my-server.internal", 8080, "local-model")

    assert result["ok"] is True
    assert result["models"] == []


def test_verify_spends_only_one_token(monkeypatch):
    """The check runs on every Connect click; it must not cost a real generation."""
    sent = {}

    class Capturing(FakeOpenAI):
        def create(self, **kwargs):
            sent.update(kwargs)
            return super().create(**kwargs)

    monkeypatch.setattr("polyglot.helper.helper.OpenAI", lambda **_: Capturing())
    verify_connection("localhost", 11434, "gpt-oss:20b")

    assert sent["max_tokens"] == 1


# ── detect_language ──────────────────────────────────────────────────────────


def test_detect_parses_the_language_and_confidence(monkeypatch):
    install(monkeypatch, content='{"language": "Spanish", "confidence": "high"}')
    result = detect_language("Hola")

    assert result["language"] == "Spanish"
    assert result["confidence"] == "high"


def test_detect_defaults_a_missing_confidence(monkeypatch):
    """The UI phrases its hint off confidence, so it must never be absent."""
    install(monkeypatch, content='{"language": "Spanish"}')

    assert detect_language("Hola")["confidence"] == "medium"


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("Spanish, obviously", id="not-json"),
        pytest.param('{"confidence": "high"}', id="no-language-key"),
        pytest.param('{"language": "  "}', id="blank-language"),
        pytest.param(None, id="empty-content"),
    ],
)
def test_detect_returns_an_error_instead_of_a_bad_guess(monkeypatch, content):
    """A malformed reply must not become a language the user then translates against."""
    install(monkeypatch, content=content)

    assert "error" in detect_language("Hola")


def test_detect_reports_an_unreachable_endpoint(monkeypatch):
    install(monkeypatch, raises=ConnectionError("Connection refused"))

    assert detect_language("Hola") == {"error": "Connection refused"}


def test_detect_truncates_a_long_document(monkeypatch):
    """Identifying a language needs a sample, not the whole text."""
    sent = {}

    class Capturing(FakeOpenAI):
        def create(self, **kwargs):
            sent["text"] = kwargs["messages"][-1]["content"]
            return super().create(**kwargs)

    monkeypatch.setattr(
        "polyglot.helper.helper.OpenAI",
        lambda **_: Capturing(content='{"language": "Spanish", "confidence": "high"}'),
    )
    detect_language("ñ" * 5000)

    assert len(sent["text"]) == 1000


# ── translate_batch ──────────────────────────────────────────────────────────


def test_batch_reassembles_by_index_even_when_reply_reorders(monkeypatch):
    """Numbered rows let the model reorder its reply without scrambling output."""
    # Return rows in reversed order
    install(
        monkeypatch,
        content='{"rows": [{"i": 1, "translations": {"Spanish": "Adiós"}}, {"i": 0, "translations": {"Spanish": "Hola"}}]}',
    )
    result = translate_batch(["Hello", "Goodbye"], ["Spanish"])

    assert result["rows"][0]["text"] == "Hello"
    assert result["rows"][0]["translations"]["Spanish"] == "Hola"
    assert result["rows"][1]["text"] == "Goodbye"
    assert result["rows"][1]["translations"]["Spanish"] == "Adiós"


def test_batch_retries_once_when_reply_is_short(monkeypatch):
    """A reply missing rows triggers exactly one retry."""
    call_count = {"count": 0}

    class CountingFake(FakeOpenAI):
        def create(self, **kwargs):
            call_count["count"] += 1
            # Both calls return incomplete data (missing row 1)
            self._content = '{"rows": [{"i": 0, "translations": {"Spanish": "Hola"}}]}'
            return super().create(**kwargs)

    monkeypatch.setattr("polyglot.helper.helper.OpenAI", lambda **_: CountingFake())
    result = translate_batch(["Hello", "Goodbye"], ["Spanish"])

    assert call_count["count"] == 2  # First attempt + 1 retry
    assert result["rows"][1]["translations"] == {}
    assert "error" in result["rows"][1]


def test_batch_missing_row_gets_error_after_retry(monkeypatch):
    """Missing row after retry comes back with error and empty translations."""
    install(
        monkeypatch,
        content='{"rows": [{"i": 0, "translations": {"Spanish": "Hola"}}]}',
    )
    result = translate_batch(["Hello", "Goodbye"], ["Spanish"])

    # Row 0 is present
    assert result["rows"][0]["translations"]["Spanish"] == "Hola"
    assert "error" not in result["rows"][0]

    # Row 1 is missing, has error
    assert result["rows"][1]["i"] == 1
    assert result["rows"][1]["text"] == "Goodbye"
    assert result["rows"][1]["translations"] == {}
    assert "error" in result["rows"][1]


def test_batch_with_usage_returns_usage_dict(monkeypatch):
    """A reply with usage block surfaces it."""
    install(
        monkeypatch,
        content='{"rows": [{"i": 0, "translations": {"Spanish": "Hola"}}]}',
        usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
    )
    result = translate_batch(["Hello"], ["Spanish"])

    assert result["usage"]["total_tokens"] == 70
    assert result["usage"]["prompt_tokens"] == 50
    assert result["usage"]["completion_tokens"] == 20


def test_batch_without_usage_returns_none(monkeypatch):
    """A reply with no usage block returns None, not zero."""
    install(
        monkeypatch,
        content='{"rows": [{"i": 0, "translations": {"Spanish": "Hola"}}]}',
    )
    result = translate_batch(["Hello"], ["Spanish"])

    assert result["usage"] is None


# ── usage tracking ───────────────────────────────────────────────────────────


def test_query_llm_surfaces_usage(monkeypatch):
    """query_llm now includes usage in its return dict."""
    install(
        monkeypatch,
        content='{"id": "polyglot_0001", "translations": []}',
        usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    )
    result = query_llm("localhost", 11434, PAYLOAD)

    assert result["usage"]["total_tokens"] == 15


def test_query_llm_without_usage_returns_none(monkeypatch):
    """A server with no usage block returns None, not zero."""
    install(monkeypatch, content='{"id": "polyglot_0001", "translations": []}')
    result = query_llm("localhost", 11434, PAYLOAD)

    assert result["usage"] is None
