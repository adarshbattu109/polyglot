"""File to house all helper functions for the project."""

import urllib3
import logging
import random
from openai import OpenAI
from constants.constants import API_KEY, HOST, MODEL, PORT, PROMPT
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)


def generate_id() -> str:
    """Generates a unique ID for translation requests.

    Returns:
        str: A unique ID in the format 'polyglot_XXXX' where XXXX is a random number.
    """
    id = f"polyglot_{random.randint(1000, 9999)}"
    logger.info(f"Generated unique ID: {id}")
    return id


def prepare_payload(text: str, target_languages: list[str]) -> dict:
    """Prepares the payload for the LLM.

    Args:
        text (str): The text to be translated.
        target_languages (list[str]): A list of target languages for translation.

    Returns:
        dict: A dictionary containing the ID, text, and target languages.
    """
    payload = {
        "id": generate_id(),
        "text": text,
        "target_languages": target_languages,
    }
    logger.info(f"Prepared payload: %s", payload)
    return payload


def query_llm(host: str, port: int, payload: dict, model: str = MODEL, api_key: str = API_KEY) -> dict:
    """Queries the LLM and returns the response.

    Args:
        host (str): The hostname of the LLM server.
        port (int): The port number of the LLM server.
        payload (dict): The payload containing text and target languages.
        model (str, optional): The model to use for translation. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.

    Returns:
        dict: The response from the LLM, parsed as a dictionary.

    Raises:
        Exception: If there's an error querying the LLM.
    """
    schema = "https" if port == 443 else "http"

    try:
        client = OpenAI(
            base_url=f"{schema}://{host}:{port}/v1",
            api_key=api_key,
            timeout=90,
        )

        logger.info(f"Initialized OpenAI client with base URL: {schema}://{host}:{port}/v1")

        messages = [
            {"role": "system", "content": f"{PROMPT}"},
            {"role": "user", "content": json.dumps(payload)},
        ]

        logger.info(f"Querying LLM at {schema}://{host}:{port}/v1 with payload: %s", payload)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        logger.info(f"LLM Response: %s", response.choices[0].message.content)
        try:
            return json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            # If response is not valid JSON, return it as plain text
            return {
                "id": payload.get("id"),
                "text": payload.get("text"),
                "translations": [{"language": "response", "translation": response.choices[0].message.content}],
                "raw_response": response.choices[0].message.content,
            }
    except Exception as e:
        result = {
            "id": payload.get("id"),
            "text": payload.get("text"),
            "translations": [],
            "error": str(e),
        }

        logger.error(f"Error querying LLM: %s", str(e))

        return result


def translate_to_languages(text: str, target_languages: list[str], host: str = HOST, port: int = PORT, model: str = MODEL, api_key: str = API_KEY) -> dict:
    """Translates text to target languages.

    Args:
        text (str): The text to be translated.
        target_languages (list[str]): A list of target languages for translation.
        host (str, optional): The hostname of the LLM server. Defaults to HOST.
        port (int, optional): The port number of the LLM server. Defaults to PORT.
        model (str, optional): The model to use for translation. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.

    Returns:
        dict: A dictionary containing the translation results with id, text, and translations.
    """
    # Create a single payload for all languages
    payload = prepare_payload(text, target_languages)

    # Query the LLM with the payload containing all target languages
    result = query_llm(host=host, port=port, payload=payload, model=model, api_key=api_key)

    return result


if __name__ == "__main__":
    # Example usage
    text = "Hello, how are you?"
    target_languages = ["Spanish", "French"]
    translations = translate_to_languages(text, target_languages)
    print(translations)
