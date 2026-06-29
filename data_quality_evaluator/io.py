from __future__ import annotations
from pathlib import Path
from io import BytesIO
import pandas as pd
import csv

def load_tabular_file(file_or_path):
    # First resolve actual filesystem paths, then fall back to file-like objects.
    if isinstance(file_or_path, (str, Path)) or hasattr(file_or_path, "__fspath__"):
        p = Path(file_or_path)
        suffix = p.suffix.lower()
        with open(p, "rb") as f:
            data = f.read()
        return _load_from_buffer(BytesIO(data), p.name, suffix)

    if hasattr(file_or_path, "read"):
        name = Path(getattr(file_or_path, "name", "uploaded.csv")).name
        suffix = Path(name).suffix.lower()
        data = file_or_path.read()
        bio = BytesIO(data)
        return _load_from_buffer(bio, name, suffix)

    raise TypeError(f"Unsupported input type: {type(file_or_path)!r}")


def load_tabular_bytes(data: bytes, source_name: str):
    suffix = Path(source_name).suffix.lower()
    return _load_from_buffer(BytesIO(data), source_name, suffix)

def _load_from_buffer(buffer: BytesIO, source_name: str, suffix: str):
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(buffer)
    else:
        sample = buffer.getvalue()[:4096].decode("utf-8", errors="ignore")
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
            sep = dialect.delimiter
        except Exception:
            sep = None
        buffer.seek(0)
        df = pd.read_csv(buffer, sep=sep, engine="python")
    df.columns = [str(c).strip() for c in df.columns]
    return df, {"source_name": source_name, "suffix": suffix}

def dataframe_to_download_bytes(df: pd.DataFrame, source_name: str, format: str = "csv") -> bytes:
    if format == "csv":
        return df.to_csv(index=False).encode("utf-8")
    bio = BytesIO()
    with pd.ExcelWriter(bio, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return bio.getvalue()
