import logging

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP

from helper.helper import translate_to_languages

logger = logging.getLogger(__name__)


app = FastAPI()


@app.post("/translate", operation_id="translate")
async def translate_text(
    payload: dict = Body(
        default={
            "text": "",
            "target_languages": [],
            "host": "",
            "port": 0,
            "model": "",
            "api_key": "",
        }
    )
):
    """Translates text to a target languages."""
    text = payload.get("text", "")
    target_languages = payload.get("target_languages", [])
    host = payload.get("host", "")
    port = payload.get("port", 0)
    model = payload.get("model", "")
    api_key = payload.get("api_key", "")
    logging.info(f"Received translation request with text: %s and target languages: %s", text, target_languages)
    result = translate_to_languages(text, target_languages, host, port, model, api_key) if text and target_languages else {"error": "Invalid input. 'text' and 'target_languages' are required."}
    return JSONResponse(content=result, status_code=200)


# Initialize and mount MCP at /mcp
mcp = FastApiMCP(app)
mcp.mount()
