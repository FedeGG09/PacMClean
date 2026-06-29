from __future__ import annotations

import json
import os
from datetime import datetime, date
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd

STATE_PATH = Path("artifacts") / "powerbi_state.json"
API_BASE = "https://api.powerbi.com/v1.0/myorg"


def load_powerbi_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_powerbi_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _json_scalar(value: Any):
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if pd.isna(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _looks_like_date_column(name: str) -> bool:
    name = (name or "").lower()
    return any(token in name for token in ("date", "fecha", "time", "timestamp", "created", "updated"))


def _infer_column_type(series: pd.Series, column_name: str) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "string"

    if pd.api.types.is_bool_dtype(series):
        return "bool"

    if pd.api.types.is_datetime64_any_dtype(series):
        return "DateTime"

    if pd.api.types.is_numeric_dtype(series):
        if pd.api.types.is_integer_dtype(series):
            return "Int64"
        return "Double"

    as_str = non_null.astype(str).str.strip()
    lowered = as_str.str.lower()
    bool_vocab = {"true", "false", "1", "0", "yes", "no", "si", "sí", "y", "n", "t", "f"}
    bool_ratio = lowered.isin(bool_vocab).mean()
    if bool_ratio >= 0.95:
        return "bool"

    numeric_ratio = pd.to_numeric(as_str.str.replace(",", ".", regex=False), errors="coerce").notna().mean()
    if numeric_ratio >= 0.95:
        if (pd.to_numeric(as_str.str.replace(",", ".", regex=False), errors="coerce") % 1 == 0).mean() >= 0.95:
            return "Int64"
        return "Double"

    date_ratio = pd.to_datetime(as_str, errors="coerce", format="mixed", dayfirst=True).notna().mean()
    if date_ratio >= 0.85 and _looks_like_date_column(column_name):
        return "DateTime"

    return "string"


def infer_powerbi_schema(df: pd.DataFrame) -> list[dict[str, str]]:
    schema = []
    for col in df.columns:
        dtype = _infer_column_type(df[col], str(col))
        schema.append({"name": str(col), "dataType": dtype})
    return schema


def _coerce_row(row: pd.Series, schema: list[dict[str, str]]) -> dict[str, Any]:
    result = {}
    type_map = {c["name"]: c["dataType"] for c in schema}
    for col, value in row.items():
        dtype = type_map.get(col, "string")
        value = _json_scalar(value)
        if value is None:
            result[col] = None
            continue
        if dtype == "Int64":
            try:
                result[col] = int(float(value))
            except Exception:
                result[col] = None
        elif dtype == "Double":
            try:
                result[col] = float(value)
            except Exception:
                result[col] = None
        elif dtype == "bool":
            if isinstance(value, bool):
                result[col] = value
            else:
                result[col] = str(value).strip().lower() in {"true", "1", "yes", "si", "sí", "y", "t"}
        elif dtype == "DateTime":
            ts = pd.to_datetime(value, errors="coerce", format="mixed", dayfirst=True)
            result[col] = None if pd.isna(ts) else ts.isoformat()
        else:
            result[col] = str(value)
    return result


def _request_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _raise_for_http_error(resp: httpx.Response, action: str):
    try:
        details = resp.json()
    except Exception:
        details = resp.text
    raise RuntimeError(f"{action} falló ({resp.status_code}): {details}")


def create_push_dataset(token: str, dataset_name: str, table_name: str, schema: list[dict[str, str]]) -> str:
    payload = {
        "name": dataset_name,
        "defaultMode": "Push",
        "tables": [
            {
                "name": table_name,
                "columns": schema,
            }
        ],
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(f"{API_BASE}/datasets", headers=_request_headers(token), json=payload)
    if resp.status_code not in (200, 201, 202):
        _raise_for_http_error(resp, "Creación del dataset")
    data = resp.json()
    dataset_id = data.get("id")
    if not dataset_id:
        raise RuntimeError("Power BI no devolvió un datasetId válido.")
    return dataset_id


def push_rows(token: str, dataset_id: str, table_name: str, rows: list[dict[str, Any]], chunk_size: int = 10000) -> int:
    total = 0
    with httpx.Client(timeout=120.0) as client:
        for start in range(0, len(rows), chunk_size):
            chunk = rows[start:start + chunk_size]
            resp = client.post(
                f"{API_BASE}/datasets/{dataset_id}/tables/{table_name}/rows",
                headers=_request_headers(token),
                json={"rows": chunk},
            )
            if resp.status_code not in (200, 201, 202):
                _raise_for_http_error(resp, "Carga de filas")
            total += len(chunk)
    return total


def publish_dataframe_to_powerbi(
    df: pd.DataFrame,
    token: str | None,
    dataset_name: str,
    table_name: str = "data",
    dataset_id: str | None = None,
) -> dict[str, Any]:
    token = (token or os.getenv("POWERBI_ACCESS_TOKEN") or "").strip()
    if not token:
        raise ValueError("Falta el access token de Power BI.")
    if df is None or df.empty:
        raise ValueError("No hay datos para exportar a Power BI.")

    schema = infer_powerbi_schema(df)
    rows = [_coerce_row(row, schema) for _, row in df.iterrows()]

    state = load_powerbi_state()
    cache_key = f"{dataset_name}::{table_name}"

    resolved_dataset_id = (dataset_id or "").strip() or state.get(cache_key) or ""
    created = False

    if not resolved_dataset_id:
        resolved_dataset_id = create_push_dataset(token, dataset_name, table_name, schema)
        state[cache_key] = resolved_dataset_id
        save_powerbi_state(state)
        created = True

    pushed = push_rows(token, resolved_dataset_id, table_name, rows)

    return {
        "status": "ok",
        "dataset_name": dataset_name,
        "table_name": table_name,
        "dataset_id": resolved_dataset_id,
        "created_dataset": created,
        "rows_sent": pushed,
        "columns": schema,
        "rows_preview": rows[:5],
        "cached_state_file": str(STATE_PATH),
    }
