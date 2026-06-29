from __future__ import annotations
from typing import Any
import pandas as pd
from .utils import parse_dates, normalize_key

def build_derived_suggestions(df: pd.DataFrame, profile: dict, findings: list[dict], rules: dict[str, Any], llm_derived: dict[str, Any] | None = None):
    suggestions = []
    for col, p in profile["profiles"].items():
        if p["is_date_candidate"]:
            suggestions.append({
                "id": f"derived_year_{col}",
                "title": f"Crear '{col}_year'",
                "description": f"Añade el año extraído de '{col}'.",
                "dtype": "int",
                "confidence": "high",
                "spec": {"source_column": col, "operation": "year", "new_column": f"{col}_year"},
            })
            suggestions.append({
                "id": f"derived_month_{col}",
                "title": f"Crear '{col}_month'",
                "description": f"Añade el mes extraído de '{col}'.",
                "dtype": "int",
                "confidence": "high",
                "spec": {"source_column": col, "operation": "month", "new_column": f"{col}_month"},
            })
        if p["is_numeric_candidate"] and not p["is_boolean_like"]:
            suggestions.append({
                "id": f"derived_bucket_{col}",
                "title": f"Crear '{col}_bucket'",
                "description": f"Segmenta '{col}' en rangos cuantiles.",
                "dtype": "category",
                "confidence": "medium",
                "spec": {"source_column": col, "operation": "quantile_bucket", "new_column": f"{col}_bucket", "q": 4},
            })
        if not p["is_numeric_candidate"] and not p["is_date_candidate"] and df[col].dtype == "object":
            suggestions.append({
                "id": f"derived_len_{col}",
                "title": f"Crear '{col}_length'",
                "description": f"Longitud del texto de '{col}'.",
                "dtype": "int",
                "confidence": "medium",
                "spec": {"source_column": col, "operation": "text_length", "new_column": f"{col}_length"},
            })
    if llm_derived and llm_derived.get("suggestions"):
        for item in llm_derived["suggestions"]:
            spec = item.get("spec")
            if spec:
                suggestions.append({
                    "id": item.get("id") or f"llm_{spec.get('new_column')}",
                    "title": item.get("title", f"Crear '{spec.get('new_column')}'"),
                    "description": item.get("description", ""),
                    "dtype": item.get("dtype", "object"),
                    "confidence": item.get("confidence", "medium"),
                    "spec": spec,
                })
    seen = set()
    deduped = []
    for s in suggestions:
        nc = s["spec"].get("new_column")
        if nc in seen:
            continue
        seen.add(nc)
        deduped.append(s)
    return deduped

def apply_derived_columns(df: pd.DataFrame, suggestions: list[dict], selected_ids: list[str]):
    out = df.copy()
    log = []
    for s in suggestions:
        if s["id"] not in selected_ids:
            continue
        spec = s["spec"]
        source = spec["source_column"]
        op = spec["operation"]
        new_col = spec["new_column"]
        if source not in out.columns:
            continue
        if op in {"year", "month"}:
            parsed = parse_dates(out[source])
            out[new_col] = parsed.dt.year if op == "year" else parsed.dt.month
        elif op == "quantile_bucket":
            num = pd.to_numeric(out[source], errors="coerce")
            q = int(spec.get("q", 4))
            try:
                out[new_col] = pd.qcut(num, q, duplicates="drop")
            except Exception:
                out[new_col] = pd.cut(num, bins=q)
        elif op == "text_length":
            out[new_col] = out[source].astype(str).str.len()
        elif op == "normalized_text":
            out[new_col] = out[source].astype(str).map(normalize_key)
        elif op == "flag_non_null":
            out[new_col] = out[source].notna().astype(int)
        log.append({"id": s["id"], "new_column": new_col, "operation": op})
    return out, log
