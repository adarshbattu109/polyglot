"""File upload and batch translation endpoints."""


def test_upload_returns_structure(client):
    """Upload a small CSV and get back columns, preview, and suggestions."""
    csv = b"text,context\nHello,greeting\nGoodbye,farewell"
    response = client.post("/upload", files={"file": ("data.csv", csv, "text/csv")})

    assert response.status_code == 200
    body = response.json()
    assert body["columns"] == ["text", "context"]
    assert body["text_columns"] == ["text", "context"]
    assert body["suggested_column"] == "text"
    assert body["row_count"] == 2
    assert len(body["preview"]) == 2


def test_upload_rejects_oversized_file(client):
    """A file with 201 rows is over the 200 limit."""
    rows = ["text\n"] + [f"row{i}\n" for i in range(201)]
    csv = "".join(rows).encode()
    response = client.post("/upload", files={"file": ("big.csv", csv, "text/csv")})

    assert response.status_code == 422
    assert "201" in response.json()["detail"]
    assert "200" in response.json()["detail"]


def test_translate_rejects_oversized_text(client):
    """A 2001-word text exceeds the word limit."""
    text = " ".join(["word"] * 2001)
    response = client.post(
        "/translate",
        json={"text": text, "target_languages": ["Spanish"]},
    )

    assert response.status_code == 422
    assert "2001" in str(response.json())


def test_translate_file_dedupes_and_batches(client, monkeypatch):
    """Duplicate cells are translated once; results spread to all rows."""
    calls = []

    def stub(texts, langs, src_lang, host, port, model, key, path):
        calls.append(texts)
        return {
            "rows": [
                {"i": i, "text": t, "translations": {l: f"{t}-{l}" for l in langs}}
                for i, t in enumerate(texts)
            ],
            "usage": None,
        }

    monkeypatch.setattr("polyglot.app.main.translate_batch", stub)

    # 27 rows total, 26 distinct → 2 batches (25 + 1); row 0 and 2 are duplicates
    rows = ["text\n", "A\n", "B\n", "A\n"] + [f"row{i}\n" for i in range(24)]
    csv = "".join(rows).encode()

    response = client.post(
        "/translate-file",
        files={"file": ("data.csv", csv, "text/csv")},
        data={
            "column": "text",
            "target_languages": ["Spanish", "French"],
            "port": 11434,
        },
    )

    assert response.status_code == 200
    body = response.json()

    # 26 distinct → ceil(26/25) = 2 batches
    assert len(calls) == 2
    assert body["spent"]["requests"] == 2
    assert body["spent"]["rows_deduped"] == 1
    assert body["spent"]["rows_translated"] == 27

    # rows 0 and 2 are both "A" → same translation
    assert body["rows"][0]["Spanish"] == "A-Spanish"
    assert body["rows"][2]["Spanish"] == "A-Spanish"


def test_translate_file_sums_usage(client, monkeypatch):
    """Usage dicts from each batch are summed."""

    def stub(texts, langs, src_lang, host, port, model, key, path):
        return {
            "rows": [
                {"i": i, "text": t, "translations": {l: f"{t}-{l}" for l in langs}}
                for i, t in enumerate(texts)
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    monkeypatch.setattr("polyglot.app.main.translate_batch", stub)

    # 26 rows → 2 batches
    rows = ["text\n"] + [f"row{i}\n" for i in range(26)]
    csv = "".join(rows).encode()

    response = client.post(
        "/translate-file",
        files={"file": ("data.csv", csv, "text/csv")},
        data={"column": "text", "target_languages": ["Spanish"]},
    )

    body = response.json()
    assert body["spent"]["input_tokens"] == 20  # 2 batches * 10
    assert body["spent"]["output_tokens"] == 40  # 2 batches * 20


def test_translate_file_usage_absent(client, monkeypatch):
    """If all batches return usage=None, spent tokens are None, not zero."""

    def stub(texts, langs, src_lang, host, port, model, key, path):
        return {
            "rows": [
                {"i": i, "text": t, "translations": {l: f"{t}-{l}" for l in langs}}
                for i, t in enumerate(texts)
            ],
            "usage": None,
        }

    monkeypatch.setattr("polyglot.app.main.translate_batch", stub)

    csv = b"text\nHello\nWorld"
    response = client.post(
        "/translate-file",
        files={"file": ("data.csv", csv, "text/csv")},
        data={"column": "text", "target_languages": ["Spanish"]},
    )

    body = response.json()
    assert body["spent"]["input_tokens"] is None
    assert body["spent"]["output_tokens"] is None


def test_translate_file_handles_errors(client, monkeypatch):
    """Rows with errors get [translation failed] in all languages."""

    def stub(texts, langs, src_lang, host, port, model, key, path):
        return {
            "rows": [
                {"i": 0, "text": texts[0], "error": "LLM unavailable"},
                {
                    "i": 1,
                    "text": texts[1],
                    "translations": {l: f"{texts[1]}-{l}" for l in langs},
                },
            ],
            "usage": None,
        }

    monkeypatch.setattr("polyglot.app.main.translate_batch", stub)

    csv = b"text\nFail\nSuccess"
    response = client.post(
        "/translate-file",
        files={"file": ("data.csv", csv, "text/csv")},
        data={"column": "text", "target_languages": ["Spanish"]},
    )

    body = response.json()
    assert body["rows"][0]["Spanish"] == "[translation failed]"
    assert body["rows"][1]["Spanish"] == "Success-Spanish"
    assert body["spent"]["rows_failed"] >= 1


def test_template_csv(client):
    """CSV template downloads with the right media type."""
    response = client.get("/template.csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert len(response.content) > 0


def test_template_json(client):
    """JSON template downloads with the right media type."""
    response = client.get("/template.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert len(response.content) > 0


def test_template_xlsx(client):
    """XLSX template downloads with the right media type."""
    response = client.get("/template.xlsx")

    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert len(response.content) > 0
