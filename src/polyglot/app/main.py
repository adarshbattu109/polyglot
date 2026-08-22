import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi_mcp import FastApiMCP
from pydantic import BaseModel, Field, StringConstraints, field_validator

from polyglot.constants.constants import (
    API_KEY,
    HOST,
    MODEL,
    PATH,
    PORT,
    PROVIDERS,
)
from polyglot.helper.batching import apply, estimate, plan
from polyglot.helper.fileops import read_upload, template, text_columns
from polyglot.helper.helper import (
    detect_language,
    translate_batch,
    translate_to_languages,
    verify_connection,
)

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
MAX_ROWS = 200
MAX_WORDS = 2000
MAX_WORKERS = 4


app = FastAPI()


# strip first, then length-check, so whitespace-only input is rejected rather than
# forwarded to the LLM as a blank prompt
NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ConnectionRequest(BaseModel):
    """Where to reach the LLM, and with what credential.

    These are caller-supplied so the UI can point at any OpenAI-compatible server. That is
    deliberate, and it means these endpoints will connect wherever they are told to — see the
    SSRF note in SECURITY.md. Omit a field to fall back to the configured default in
    constants.py.
    """

    host: NonBlank = HOST
    port: int = Field(default=PORT, ge=1, le=65535)
    # the base path the API is served under: /v1 for most, /v1beta/openai for Gemini
    path: NonBlank = PATH
    model: NonBlank = MODEL
    api_key: str = API_KEY


class TranslationRequest(ConnectionRequest):
    """Request body for /translate: what to translate, and where to have it done."""

    text: NonBlank
    target_languages: list[NonBlank] = Field(min_length=1)
    # blank means "let the model identify it" — the prompt handles either case
    source_language: str = ""

    @field_validator("text")
    @classmethod
    def check_word_count(cls, v: str) -> str:
        word_count = len(v.split())
        if word_count > MAX_WORDS:
            raise ValueError(f"Text has {word_count} words; the limit is {MAX_WORDS}.")
        return v


class DetectRequest(ConnectionRequest):
    """Text to identify, plus where to ask."""

    text: NonBlank


@app.get("/", include_in_schema=False)
def index():
    """Serves the single-page translation UI."""
    # no-cache: the UI is a single file that changes often; a stale disk-cached copy makes a
    # browser show an old build after an update. Revalidate every load.
    return FileResponse(
        STATIC_DIR / "index.html", headers={"Cache-Control": "no-cache"}
    )


@app.get("/config", operation_id="config")
def config():
    """The configured LLM defaults, so the UI can prefill its connection fields.

    Deliberately omits api_key — a GET that echoes a credential back is a credential leak.
    """
    return {
        "host": HOST,
        "port": PORT,
        "path": PATH,
        "model": MODEL,
        "providers": PROVIDERS,
    }


@app.post("/verify", operation_id="verify")
def verify(request: ConnectionRequest):
    """Checks that the given endpoint answers and accepts the key, before any translating.

    Returns 502 on an unusable endpoint so a failure is a failure to the caller, not a 200
    with ok=false buried in the body.
    """
    logger.info(
        "Verifying connection to %s:%s%s for model %s",
        request.host,
        request.port,
        request.path,
        request.model,
    )
    result = verify_connection(
        host=request.host,
        port=request.port,
        model=request.model,
        api_key=request.api_key,
        path=request.path,
    )
    return JSONResponse(content=result, status_code=200 if result["ok"] else 502)


@app.post("/detect", operation_id="detect")
def detect(request: DetectRequest):
    """Identifies the language of the given text, as a suggestion the caller can correct."""
    logger.info("Detecting the language of %s characters", len(request.text))
    result = detect_language(
        request.text,
        host=request.host,
        port=request.port,
        model=request.model,
        api_key=request.api_key,
        path=request.path,
    )
    if result.get("error"):
        return JSONResponse(content=result, status_code=502)
    return JSONResponse(content=result, status_code=200)


@app.post("/translate", operation_id="translate")
def translate_text(request: TranslationRequest):
    """Translates text to a target languages."""
    logger.info(
        "Received translation request with text: %s and target languages: %s",
        request.text,
        request.target_languages,
    )
    result = translate_to_languages(
        request.text,
        request.target_languages,
        source_language=request.source_language,
        host=request.host,
        port=request.port,
        model=request.model,
        api_key=request.api_key,
        path=request.path,
    )
    if result.get("error"):
        return JSONResponse(content=result, status_code=502)
    return JSONResponse(content=result, status_code=200)


@app.post("/upload", operation_id="upload")
def upload_file(file: UploadFile = File(...)):
    """Parse an uploaded file and return its structure; no translation yet."""
    data = file.file.read()
    try:
        df = read_upload(data, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"File has {len(df)} rows; the limit is {MAX_ROWS}.",
        )

    text_cols = text_columns(df)
    suggested = (
        "text" if "text" in df.columns else (text_cols[0] if text_cols else None)
    )

    return {
        "columns": list(df.columns),
        "text_columns": text_cols,
        "suggested_column": suggested,
        "row_count": len(df),
        "preview": df.head(3).where(df.notna(), None).to_dict("records"),
    }


@app.post("/translate-file", operation_id="translate_file")
def translate_file(
    file: UploadFile = File(...),
    column: str = Form(...),
    target_languages: list[str] = Form(...),
    source_language: str = Form(""),
    host: str = Form(HOST),
    port: int = Form(PORT),
    path: str = Form(PATH),
    model: str = Form(MODEL),
    api_key: str = Form(API_KEY),
):
    """Batch-translate a column in an uploaded file."""
    data = file.file.read()
    try:
        df = read_upload(data, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if len(df) > MAX_ROWS:
        raise HTTPException(
            status_code=422,
            detail=f"File has {len(df)} rows; the limit is {MAX_ROWS}.",
        )

    if column not in df.columns:
        raise HTTPException(
            status_code=422, detail=f"Column '{column}' not found in file."
        )

    cells = df[column].astype(str).tolist()
    est = estimate(cells, target_languages)
    chunks = plan(cells)

    translations = {}
    failed_sources = set()
    usages = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(
                translate_batch,
                chunk,
                target_languages,
                source_language,
                host,
                port,
                model,
                api_key,
                path,
            ): chunk
            for chunk in chunks
        }

        for future in as_completed(futures):
            chunk = futures[future]
            result = future.result()
            usages.append(result.get("usage"))

            for row in result.get("rows", []):
                src = chunk[row["i"]]
                if row.get("error"):
                    failed_sources.add(src)
                    translations[src] = {
                        lang: "[translation failed]" for lang in target_languages
                    }
                else:
                    translations[src] = row["translations"]

    out = apply(df, column, translations, target_languages)

    failed_rows = sum(1 for cell in cells if cell in failed_sources)
    rows_translated = len(df) - failed_rows
    rows_deduped = est["duplicate_rows"]

    if any(u is not None for u in usages):
        input_tokens = sum(u["prompt_tokens"] for u in usages if u)
        output_tokens = sum(u["completion_tokens"] for u in usages if u)
    else:
        input_tokens = None
        output_tokens = None

    return {
        "column": column,
        "languages": target_languages,
        "columns": list(out.columns),
        "rows": out.where(out.notna(), None).to_dict("records"),
        "estimate": est,
        "spent": {
            "requests": len(chunks),
            "rows_translated": rows_translated,
            "rows_deduped": rows_deduped,
            "rows_failed": failed_rows,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        },
    }


@app.get("/template.{fmt}", operation_id="template")
def get_template(fmt: str):
    """Download a template file for batch translation."""
    if fmt not in {"csv", "xlsx", "json"}:
        raise HTTPException(status_code=422, detail=f"Unknown format: {fmt}")

    media_types = {
        "csv": "text/csv",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "json": "application/json",
    }

    return Response(
        content=template(fmt),
        media_type=media_types[fmt],
        headers={
            "Content-Disposition": f"attachment; filename=polyglot-template.{fmt}"
        },
    )


# Initialize and mount MCP at /mcp
mcp = FastApiMCP(app)
mcp.mount()
