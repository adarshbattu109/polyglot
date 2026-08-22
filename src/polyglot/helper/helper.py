"""File to house all helper functions for the project."""

import json
import logging
import random

import urllib3
from openai import OpenAI

from polyglot.constants.constants import (
    API_KEY,
    BATCH_PROMPT,
    DETECT_PROMPT,
    HOST,
    MODEL,
    PATH,
    PORT,
    PROMPT,
)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


logger = logging.getLogger(__name__)


def _usage(response) -> dict | None:
    """The provider's authoritative token count from an OpenAI-compatible reply, or None if
    the endpoint omitted it (some self-hosted servers do). A missing count must be None, never
    zero — the UI renders None as 'not reported' and zero as a free request."""
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }


def generate_id() -> str:
    """Generates a unique ID for translation requests.

    Returns:
        str: A unique ID in the format 'polyglot_XXXX' where XXXX is a random number.
    """
    id = f"polyglot_{random.randint(1000, 9999)}"
    logger.info(f"Generated unique ID: {id}")
    return id


def base_url(host: str, port: int, path: str = PATH) -> str:
    """Builds the OpenAI-compatible base URL for a host, port and base path.

    HTTPS only on 443. Any other port is plain HTTP, which sends the text and the key in the
    clear — see SECURITY.md. The UI's endpoint preview mirrors this rule.

    Args:
        host (str): The hostname of the LLM server.
        port (int): The port number of the LLM server.
        path (str, optional): The base path the API is served under. Defaults to PATH.

    Returns:
        str: e.g. ``https://ollama.com:443/v1``.
    """
    schema = "https" if port == 443 else "http"
    return f"{schema}://{host}:{port}/{path.strip('/')}"


def prepare_payload(
    text: str, target_languages: list[str], source_language: str = ""
) -> dict:
    """Prepares the payload for the LLM.

    Args:
        text (str): The text to be translated.
        target_languages (list[str]): A list of target languages for translation.
        source_language (str, optional): The language the text is in. Blank asks the model to
            identify it, which is the default.

    Returns:
        dict: A dictionary containing the ID, text, source and target languages.
    """
    payload = {
        "id": generate_id(),
        "text": text,
        "source_language": source_language,
        "target_languages": target_languages,
    }
    logger.info("Prepared payload: %s", payload)
    return payload


def verify_connection(
    host: str,
    port: int,
    model: str = MODEL,
    api_key: str = API_KEY,
    path: str = PATH,
) -> dict:
    """Checks that an endpoint is reachable, the key is accepted, and the model answers.

    Two calls, because neither alone is enough:

    * ``/v1/models`` gives the list the UI offers as choices — but it is not always
      authenticated. Ollama serves it to an invalid key, so a successful listing does not
      prove the credential is good.
    * a one-token completion is therefore the authoritative check. It is what proves the key
      is accepted *and* that this particular model is usable on this plan, which is the
      failure a user actually hits (a 403 "model requires a subscription" on a model the
      listing happily advertised).

    Args:
        host (str): The hostname of the LLM server.
        port (int): The port number of the LLM server.
        model (str, optional): The model to exercise. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.
        path (str, optional): The API base path. Defaults to PATH.

    Returns:
        dict: ``{"ok": True, "models": [...], "model_available": bool}`` if the model answered,
        or ``{"ok": False, "error": str, "models": [...]}`` if it did not. ``models`` is
        included either way — a rejected model with a good listing is exactly when the user
        needs to see the alternatives.
    """
    url = base_url(host, port, path)
    client = OpenAI(base_url=url, api_key=api_key, timeout=20)

    models: list[str] = []
    try:
        models = sorted(m.id for m in client.models.list().data)
    # A missing or unauthenticated listing is not fatal: some servers don't implement it, and
    # the completion below is what decides. Only log it.
    except Exception as e:  # noqa: BLE001
        logger.info("No model listing from %s: %s", url, e)

    try:
        client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
    # deliberately broad, as in query_llm: connection, auth, and model-refusal failures all
    # mean "you cannot translate with this", and the message is what the user needs to see.
    except Exception as e:  # noqa: BLE001
        logger.error("Verification failed for %s: %s", url, e)
        return {"ok": False, "error": str(e), "models": models}

    logger.info("Verified %s with %s — %s models listed", url, model, len(models))
    return {
        "ok": True,
        "models": models,
        "model_available": not models or model in models,
    }


def detect_language(
    text: str,
    host: str = HOST,
    port: int = PORT,
    model: str = MODEL,
    api_key: str = API_KEY,
    path: str = PATH,
) -> dict:
    """Asks the model which language a piece of text is written in.

    Only the first 1000 characters are sent — that is more than enough to identify a language,
    and it keeps a long document from being uploaded just to label it.

    Args:
        text (str): The text to identify.
        host (str, optional): The hostname of the LLM server. Defaults to HOST.
        port (int, optional): The port number of the LLM server. Defaults to PORT.
        model (str, optional): The model to use. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.
        path (str, optional): The API base path. Defaults to PATH.

    Returns:
        dict: ``{"language": str, "confidence": str}``, or ``{"error": str}`` if the model
        could not be reached or did not answer in the expected shape.
    """
    try:
        client = OpenAI(
            base_url=base_url(host, port, path), api_key=api_key, timeout=45
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": DETECT_PROMPT},
                {"role": "user", "content": text[:1000]},
            ],
        )
        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ValueError("LLM returned an empty response.")

        parsed = json.loads(content)
        language = str(parsed.get("language", "")).strip()
        if not language:
            raise ValueError(f"No language in the model's reply: {content[:200]}")

        logger.info("Detected language: %s", language)
        return {
            "language": language,
            "confidence": str(parsed.get("confidence", "")).strip() or "medium",
            "usage": _usage(response),
        }
    # deliberately broad, as in query_llm: connection, auth and malformed-reply failures are
    # all just "detection didn't work", and the user can still type the language in.
    except Exception as e:  # noqa: BLE001
        logger.error("Error detecting language: %s", e)
        return {"error": str(e)}


def query_llm(
    host: str,
    port: int,
    payload: dict,
    model: str = MODEL,
    api_key: str = API_KEY,
    path: str = PATH,
) -> dict:
    """Queries the LLM and returns the response.

    Args:
        host (str): The hostname of the LLM server.
        port (int): The port number of the LLM server.
        payload (dict): The payload containing text and target languages.
        model (str, optional): The model to use for translation. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.
        path (str, optional): The API base path. Defaults to PATH.

    Returns:
        dict: The response from the LLM, parsed as a dictionary.

    Raises:
        Exception: If there's an error querying the LLM.
    """
    url = base_url(host, port, path)

    try:
        client = OpenAI(base_url=url, api_key=api_key, timeout=90)

        messages = [
            {"role": "system", "content": f"{PROMPT}"},
            {"role": "user", "content": json.dumps(payload)},
        ]

        logger.info("Querying LLM at %s with payload: %s", url, payload)

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ValueError("LLM returned an empty response.")

        logger.info("LLM Response: %s", content)
        try:
            result = json.loads(content)
            result["usage"] = _usage(response)
            return result
        except json.JSONDecodeError:
            # If response is not valid JSON, return it as plain text
            return {
                "id": payload.get("id"),
                "text": payload.get("text"),
                "translations": [{"language": "response", "translation": content}],
                "raw_response": content,
                "usage": _usage(response),
            }
    # deliberately broad: any upstream failure (connection, auth, timeout, bad payload)
    # becomes a structured error the endpoint turns into a 502. Narrowing this would let
    # some of them escape as an unhandled 500 with no id to correlate against.
    except Exception as e:  # noqa: BLE001
        result = {
            "id": payload.get("id"),
            "text": payload.get("text"),
            "translations": [],
            "error": str(e),
            "usage": None,
        }

        logger.error("Error querying LLM: %s", str(e))

        return result


def translate_to_languages(
    text: str,
    target_languages: list[str],
    source_language: str = "",
    host: str = HOST,
    port: int = PORT,
    model: str = MODEL,
    api_key: str = API_KEY,
    path: str = PATH,
) -> dict:
    """Translates text to target languages.

    Args:
        text (str): The text to be translated.
        target_languages (list[str]): A list of target languages for translation.
        source_language (str, optional): The language the text is in. Blank asks the model to
            identify it, which is the default.
        host (str, optional): The hostname of the LLM server. Defaults to HOST.
        port (int, optional): The port number of the LLM server. Defaults to PORT.
        model (str, optional): The model to use for translation. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.
        path (str, optional): The API base path. Defaults to PATH.

    Returns:
        dict: A dictionary containing the translation results with id, text, and translations.
    """
    # Create a single payload for all languages
    payload = prepare_payload(text, target_languages, source_language)

    # Query the LLM with the payload containing all target languages
    result = query_llm(
        host=host,
        port=port,
        payload=payload,
        model=model,
        api_key=api_key,
        path=path,
    )

    return result


def translate_batch(
    texts: list[str],
    target_languages: list[str],
    source_language: str = "",
    host: str = HOST,
    port: int = PORT,
    model: str = MODEL,
    api_key: str = API_KEY,
    path: str = PATH,
) -> dict:
    """Translates a batch of texts to target languages in a single LLM request.

    Each text is numbered to prevent reply reordering from scrambling output. Retries once if the
    reply is malformed or short. Missing rows after retry come back with empty translations and an
    error field.

    Args:
        texts (list[str]): The texts to be translated.
        target_languages (list[str]): A list of target languages for translation.
        source_language (str, optional): The language the texts are in. Blank asks the model to
            identify it, which is the default.
        host (str, optional): The hostname of the LLM server. Defaults to HOST.
        port (int, optional): The port number of the LLM server. Defaults to PORT.
        model (str, optional): The model to use for translation. Defaults to MODEL.
        api_key (str, optional): The API key for authentication. Defaults to API_KEY.
        path (str, optional): The API base path. Defaults to PATH.

    Returns:
        dict: ``{"rows": [{"i": int, "text": str, "translations": {lang: str}, "error": str?}, ...],
        "usage": dict | None}``
    """
    url = base_url(host, port, path)
    payload = {
        "source_language": source_language,
        "target_languages": target_languages,
        "rows": [{"i": i, "text": text} for i, text in enumerate(texts)],
    }

    def _attempt():
        """Makes one LLM request and returns (parsed_rows_by_index, usage, error_message)."""
        try:
            client = OpenAI(base_url=url, api_key=api_key, timeout=90)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": BATCH_PROMPT},
                    {"role": "user", "content": json.dumps(payload)},
                ],
            )
            content = response.choices[0].message.content if response.choices else None
            if not content:
                return {}, None, "LLM returned an empty response."

            parsed = json.loads(content)
            rows = parsed.get("rows", [])
            if not rows:
                return {}, None, "Reply missing 'rows' key or rows are empty."

            by_index = {row["i"]: row for row in rows if "i" in row}
            return by_index, _usage(response), None

        except json.JSONDecodeError:
            return {}, None, "Reply was not valid JSON."
        except Exception as e:  # noqa: BLE001
            return {}, None, str(e)

    # First attempt
    by_index, usage, error = _attempt()
    missing = set(range(len(texts))) - by_index.keys()

    # Retry once if malformed or short
    if error or missing:
        logger.info(
            "Batch translation attempt 1 failed or short, retrying: %s",
            error or "missing rows",
        )
        by_index_retry, usage_retry, error_retry = _attempt()
        # Take the retry's data if it succeeded or got further
        if not error_retry:
            by_index.update(by_index_retry)
            usage = usage_retry
        missing = set(range(len(texts))) - by_index.keys()

    # Assemble result in input order; a row absent even after the retry is marked, not dropped
    result_rows = []
    for i, text in enumerate(texts):
        row = by_index.get(i)
        if row is not None:
            result_rows.append(
                {"i": i, "text": text, "translations": row.get("translations", {})}
            )
        else:
            result_rows.append(
                {
                    "i": i,
                    "text": text,
                    "translations": {},
                    "error": "Row missing from LLM reply after retry.",
                }
            )

    logger.info("Batch translated %d rows, %d missing", len(texts), len(missing))
    return {"rows": result_rows, "usage": usage}


if __name__ == "__main__":
    # Example usage
    text = "Hello, how are you?"
    target_languages = ["Spanish", "French"]
    translations = translate_to_languages(text, target_languages)
    print(translations)
