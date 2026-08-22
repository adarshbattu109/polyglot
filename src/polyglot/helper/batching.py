import math

BATCH_SIZE = 25
MESSAGE_OVERHEAD = 40
MESSAGES_PER_REQUEST = 2


def plan(strings: list[str], batch_size: int = BATCH_SIZE) -> list[list[str]]:
    """Order-preserving dedupe of `strings`, then chunk into lists of <= batch_size.
    Duplicates removed keeping first occurrence order (use dict.fromkeys)."""
    distinct = list(dict.fromkeys(strings))
    return [distinct[i : i + batch_size] for i in range(0, len(distinct), batch_size)]


def estimate(
    strings: list[str], target_languages: list[str], batch_size: int = BATCH_SIZE
) -> dict:
    """Warn about spend BEFORE translating. Uses UTF-8 BYTES, not characters."""
    if not strings:
        return {
            "requests": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "distinct_rows": 0,
            "duplicate_rows": 0,
        }

    # ponytail: this formula is reimplemented in index.html fileEstimate() so the live UI
    # estimate needs no server round-trip on every checkbox click — change both together.
    distinct = list(dict.fromkeys(strings))
    requests = math.ceil(len(distinct) / batch_size)
    text_tokens = sum(len(s.encode("utf-8")) / 4 for s in distinct)
    input_tokens = round(
        text_tokens + MESSAGE_OVERHEAD * MESSAGES_PER_REQUEST * requests
    )
    output_tokens = round(text_tokens * len(target_languages) * 1.3)

    return {
        "requests": requests,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "distinct_rows": len(distinct),
        "duplicate_rows": len(strings) - len(distinct),
    }


def apply(
    df, column: str, translations: dict[str, dict[str, str]], languages: list[str]
):
    """Map distinct results back onto every row."""
    result = df.copy()
    for lang in languages:
        # bind lang per iteration so the lambda captures each language, not the loop's last
        result[lang] = df[column].apply(
            lambda text, lang=lang: translations.get(text, {}).get(lang, "")
        )
    return result
