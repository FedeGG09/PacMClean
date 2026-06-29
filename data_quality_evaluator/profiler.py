from __future__ import annotations
from typing import Any
import pandas as pd
from .utils import looks_numeric, looks_date, normalize_text, normalize_key, safe_div

def profile_dataframe(df: pd.DataFrame, cfg, rules: dict[str, Any] | None = None) -> dict[str, Any]:
    rules = rules or {}
    profiles = {}
    for col in df.columns:
        s = df[col]
        non_null = s.dropna()
        sample = [normalize_text(v) for v in non_null.astype(str).head(cfg.max_sample_values).tolist()]
        profile = {
            "column": col,
            "dtype_raw": str(s.dtype),
            "nulls": int(s.isna().sum()),
            "null_pct": round(s.isna().mean() * 100, 2),
            "n_unique": int(non_null.nunique(dropna=True)),
            "top_values": [],
            "sample_values": sample,
            "is_numeric_candidate": bool(looks_numeric(s)),
            "is_date_candidate": bool(looks_date(s, column_name=col)),
            "is_boolean_like": bool(s.dropna().astype(str).str.lower().isin(["true","false","1","0","yes","no","si","sí","y","n","t","f"]).mean() > 0.8 if len(non_null) else False),
        }
        if len(non_null):
            vc = non_null.astype(str).map(normalize_key).value_counts().head(5)
            profile["top_values"] = [{"value": k, "count": int(v), "pct": round(safe_div(v, len(s)) * 100, 2)} for k, v in vc.items()]
        if profile["is_numeric_candidate"]:
            num = pd.to_numeric(s.astype(str).str.replace(",", ".", regex=False), errors="coerce")
            profile["numeric"] = {
                "min": None if num.dropna().empty else float(num.min()),
                "max": None if num.dropna().empty else float(num.max()),
                "mean": None if num.dropna().empty else float(num.mean()),
                "median": None if num.dropna().empty else float(num.median()),
            }
        if profile["is_date_candidate"]:
            parsed = pd.to_datetime(s, errors="coerce", format="mixed", dayfirst=True)
            profile["date"] = {
                "valid_pct": round(parsed.notna().mean() * 100, 2),
                "min": None if parsed.dropna().empty else parsed.min().isoformat(),
                "max": None if parsed.dropna().empty else parsed.max().isoformat(),
            }
        profiles[col] = profile

    inferred_schema = {}
    for col, prof in profiles.items():
        if prof["is_numeric_candidate"] and not prof["is_date_candidate"]:
            inferred_schema[col] = "numeric"
        elif prof["is_date_candidate"] and not prof["is_numeric_candidate"]:
            inferred_schema[col] = "date"
        elif prof["is_boolean_like"]:
            inferred_schema[col] = "boolean"
        else:
            inferred_schema[col] = "categorical/text"
    return {
        "row_count": int(len(df)),
        "col_count": int(df.shape[1]),
        "profiles": profiles,
        "inferred_schema": inferred_schema,
    }
