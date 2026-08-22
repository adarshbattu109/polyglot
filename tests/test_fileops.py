"""Tests for fileops module."""

import pandas
import pandas.testing
import pytest

from polyglot.helper.fileops import read_upload, template, text_columns, to_download


def test_csv_roundtrip():
    df = pandas.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    data = to_download(df, "csv")
    result = read_upload(data, "test.csv")
    pandas.testing.assert_frame_equal(result, df)


def test_xlsx_roundtrip():
    df = pandas.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    data = to_download(df, "xlsx")
    result = read_upload(data, "test.xlsx")
    pandas.testing.assert_frame_equal(result, df)


def test_json_roundtrip():
    df = pandas.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    data = to_download(df, "json")
    result = read_upload(data, "test.json")
    # JSON may lose dtype precision, compare values
    assert result.to_dict("records") == df.to_dict("records")


def test_csv_non_latin_roundtrip():
    """CSV with non-Latin text preserves characters via BOM encoding."""
    df = pandas.DataFrame({"text": ["నమస్తే", "नमस्ते", "Hello"]})
    data = to_download(df, "csv")
    result = read_upload(data, "example.csv")
    pandas.testing.assert_frame_equal(result, df)


def test_text_columns():
    df = pandas.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
    assert text_columns(df) == ["name"]


def test_read_upload_invalid_extension():
    with pytest.raises(ValueError, match="Unsupported extension"):
        read_upload(b"data", "file.txt")


def test_template_csv():
    data = template("csv")
    df = read_upload(data, "template.csv")
    assert "text" in df.columns
    assert len(df) == 3
