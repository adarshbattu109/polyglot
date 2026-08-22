"""File I/O for translation uploads and downloads."""

import io

import pandas


def read_upload(data: bytes, filename: str) -> pandas.DataFrame:
    """Parse uploaded file bytes into a DataFrame.

    Dispatches on filename extension: .csv, .xlsx, .json.
    CSV read with utf-8-sig to strip Excel BOM.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    buf = io.BytesIO(data)

    if ext == "csv":
        return pandas.read_csv(buf, encoding="utf-8-sig")
    if ext == "xlsx":
        return pandas.read_excel(buf)
    if ext == "json":
        return pandas.read_json(buf)
    raise ValueError(f"Unsupported extension .{ext}; use .csv, .xlsx, or .json")


def text_columns(df: pandas.DataFrame) -> list[str]:
    """Return string column names, order preserved."""
    return [col for col in df.columns if pandas.api.types.is_string_dtype(df[col])]


def to_download(df: pandas.DataFrame, format: str) -> bytes:
    """Export DataFrame to bytes in the given format.

    CSV uses utf-8-sig (BOM) so Excel opens non-Latin scripts correctly.
    """
    buf = io.BytesIO()

    if format == "csv":
        df.to_csv(buf, index=False, encoding="utf-8-sig")
    elif format == "xlsx":
        df.to_excel(buf, index=False)
    elif format == "json":
        return df.to_json(orient="records", force_ascii=False).encode("utf-8")
    else:
        raise ValueError(f"Unsupported format {format!r}; use csv, xlsx, or json")

    return buf.getvalue()


def template(format: str) -> bytes:
    """Generate a 3-row example DataFrame for download."""
    df = pandas.DataFrame({"text": ["Hello", "World", "Example"]})
    return to_download(df, format)
