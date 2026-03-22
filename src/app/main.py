import logging

from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
from fastapi_mcp import FastApiMCP
from helper.helper import translate_to_languages

logger = logging.getLogger(__name__)


app = FastAPI()


@app.post("/translate", operation_id="translate")
async def translate_text(payload: dict = Body(default={"text": "", "target_languages": []})):
    """Translates text to a target languages."""
    text = payload.get("text", "")
    target_languages = payload.get("target_languages", [])
    logging.info(f"Received translation request with text: %s and target languages: %s", text, target_languages)
    result = translate_to_languages(text, target_languages) if text and target_languages else {"error": "Invalid input. 'text' and 'target_languages' are required."}
    print(result)
    return JSONResponse(content=result, status_code=200)


# Initialize and mount MCP at /mcp
mcp = FastApiMCP(app)
mcp.mount()
