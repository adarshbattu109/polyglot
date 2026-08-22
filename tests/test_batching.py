import pandas as pd

from polyglot.helper.batching import (
    MESSAGE_OVERHEAD,
    MESSAGES_PER_REQUEST,
    apply,
    estimate,
    plan,
)


def test_plan_dedupes_and_chunks():
    result = plan(["a", "b", "a", "c", "d", "b", "e"], batch_size=2)
    assert result == [["a", "b"], ["c", "d"], ["e"]]


def test_estimate_counts_bytes_not_chars():
    # Telugu string with 6 characters but 18 bytes (3 bytes per char)
    telugu = "నమస్తే"
    # Latin string with 6 characters and 6 bytes
    latin = "abcdef"

    assert len(telugu) == len(latin) == 6
    assert len(telugu.encode("utf-8")) == 18
    assert len(latin.encode("utf-8")) == 6

    telugu_result = estimate([telugu], ["Spanish"])
    latin_result = estimate([latin], ["Spanish"])

    # Telugu should produce strictly more input_tokens than Latin
    assert telugu_result["input_tokens"] > latin_result["input_tokens"]

    # Verify exact Telugu calculation: round(18/4 + 40*2*1) = round(4.5 + 80) = 84
    expected_telugu = round(18 / 4 + MESSAGE_OVERHEAD * MESSAGES_PER_REQUEST * 1)
    assert telugu_result["input_tokens"] == expected_telugu == 84


def test_output_tokens_scale_with_languages():
    strings = ["test"]
    one_lang = estimate(strings, ["Spanish"])
    three_lang = estimate(strings, ["Spanish", "French", "German"])

    # Output tokens should scale with number of languages (within rounding)
    assert abs(three_lang["output_tokens"] - 3 * one_lang["output_tokens"]) <= 1


def test_distinct_and_duplicate_rows():
    strings = ["a", "b", "a", "c", "a"]
    result = estimate(strings, ["Spanish"])

    assert result["distinct_rows"] == 3
    assert result["duplicate_rows"] == 2


def test_requests_ceil_batch_size():
    strings = [str(i) for i in range(30)]
    result = estimate(strings, ["Spanish"], batch_size=25)

    assert result["requests"] == 2


def test_apply_handles_duplicates_and_missing():
    df = pd.DataFrame({"text": ["apple", "banana", "apple", "cherry"]})
    translations = {
        "apple": {"Spanish": "manzana", "French": "pomme"},
        "banana": {"Spanish": "plátano", "French": "banane"},
        # "cherry" intentionally missing
    }

    result = apply(df, "text", translations, ["Spanish", "French"])

    # Check structure
    assert list(result.columns) == ["text", "Spanish", "French"]
    assert len(result) == 4

    # Check duplicate handling (both "apple" rows get same translation)
    assert result["Spanish"].tolist() == ["manzana", "plátano", "manzana", ""]
    assert result["French"].tolist() == ["pomme", "banane", "pomme", ""]


def test_estimate_empty_strings():
    result = estimate([], ["Spanish"])
    assert result == {
        "requests": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "distinct_rows": 0,
        "duplicate_rows": 0,
    }
