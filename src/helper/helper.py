"""File to house all helper functions for the project."""

import urllib3
import logging
import random
import concurrent
from openai import OpenAI
from tqdm import tqdm
from constants.constants import API_KEY, HOST, MODEL, PORT, PROMPT
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)


def generate_id() -> str:
    id = f"polyglot_{random.randint(1000, 9999)}"
    logger.info(f"Generated unique ID: {id}")
    return id


def prepare_payload(text: str, target_languages: list[str]) -> dict:
    """Prepares the payload for the LLM."""
    payload = {
        "id": generate_id(),
        "text": text,
        "target_languages": target_languages,
    }
    logger.info(f"Prepared payload: %s", payload)
    return payload


def query_llm(host: str, port: int, payload: dict, model: str = MODEL, api_key: str = API_KEY) -> str:
    """Queries the LLM and returns the response."""
    schema = "https" if port == 443 else "http"
    logger.info(f"Querying LLM at {schema}://{host}:{port}/v1 with payload: %s", payload)

    try:
        client = OpenAI(
            base_url=f"{schema}://{host}:{port}/v1",
            api_key=api_key,
            timeout=90,
        )

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"{PROMPT}"},
                {"role": "user", "content": json.dumps(payload)},
            ],
        )

        # Print the model's response
        logging.info(f"LLM Response: %s", response.choices[0].message.content)
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        result = {
            "id": payload.get("id"),
            "text": payload.get("text"),
            "translations": [],
            "error": str(e),
        }
        logging.error(f"Error querying LLM: %s", str(e))

        return result


def translate_to_languages(text: str, target_languages: list[str], host: str = HOST, port: int = PORT, model: str = MODEL, api_key: str = API_KEY) -> dict:
    """Translates text to a target languages."""
    # Placeholder implementation for translation logic
    result = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=None) as executor:
        futures = [executor.submit(query_llm, host=host, port=port, payload=prepare_payload(text, target_languages), model=model, api_key=api_key)]
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures)):
            result.append(future.result())  # Wait for all translations to complete
    return result


if __name__ == "__main__":
    # Example usage
    text = "Hello, how are you?"
    target_languages = ["Spanish", "French"]
    translations = translate_to_languages(text, target_languages)
    print(translations)
