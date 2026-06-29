from __future__ import annotations
import re
import json
from datetime import datetime, date
import pandas as pd
import numpy as np
from rapidfuzz import fuzz

DATE_PATTERNS = [
    r"^\d{4}-\d{2}-\d{2}$",
    r"^\d{2}/\d{2}/\d{4}$",
    r"^\d{2}-\d{2}-\d{4}$",
    r"^\d{4}/\d{2}/\d{2}$",
    r"^\d{2}\.\d{2}\.\d{4}$",
]

def safe_json(obj):
    def default(o):
        if isinstance(o, (datetime, date, pd.Timestamp)):
            return o.isoformat()
        if isinstance(o, (np.integer, np.floating)):
            return float(o)
        if isinstance(o, (np.bool_, bool)):
            return bool(o)
        if pd.isna(o):
            return None
        return str(o)
    return json.loads(json.dumps(obj, default=default, ensure_ascii=False))

def normalize_text(s):
    if pd.isna(s):
        return s
    return re.sub(r"\s+", " ", str(s)).strip()

def normalize_key(s):
    if pd.isna(s):
        return s
    return normalize_text(s).lower()

def is_boolean_like(series: pd.Series) -> bool:
    vals = set(str(v).strip().lower() for v in series.dropna().unique().tolist()[:20])
    return vals.issubset({"true", "false", "1", "0", "yes", "no", "si", "sí", "y", "n", "t", "f"}) and len(vals) > 0

def looks_numeric(series: pd.Series, threshold: float = 0.8) -> bool:
    s = series.dropna().astype(str).str.replace(",", ".", regex=False)
    coerced = pd.to_numeric(s, errors="coerce")
    ratio = coerced.notna().mean() if len(coerced) else 0
    return ratio >= threshold

def looks_date(series: pd.Series, threshold: float = 0.6, column_name: str | None = None) -> bool:
    s = series.dropna().astype(str).map(normalize_text)
    if s.empty:
        return False

    pattern_hits = s.map(lambda x: any(re.match(p, x or "") for p in DATE_PATTERNS)).mean()
    if pattern_hits >= threshold:
        return True

    name = (column_name or "").lower()
    name_hint = any(token in name for token in ("date", "fecha", "time", "timestamp", "created", "updated", "birth", "inicio", "fin"))

    # Only allow a broader parse heuristic when the column name suggests a date field.
    if name_hint:
        parsed = pd.to_datetime(s, errors="coerce", format="mixed", dayfirst=True)
        return parsed.notna().mean() >= threshold

    return False

def parse_dates(series: pd.Series):
    return pd.to_datetime(series, errors="coerce", format="mixed", dayfirst=True)

def iqr_outlier_mask(x: pd.Series, multiplier: float = 1.5):
    s = pd.to_numeric(x, errors="coerce")
    s = s[~s.isna()]
    if len(s) < 4:
        return pd.Series([False] * len(x), index=x.index)
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0 or pd.isna(iqr):
        return pd.Series([False] * len(x), index=x.index)
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr
    return (pd.to_numeric(x, errors="coerce") < lower) | (pd.to_numeric(x, errors="coerce") > upper)

def fuzzy_canonical_map(values, threshold: int = 90):
    values = [normalize_key(v) for v in values if pd.notna(v)]
    canon = []
    mapping = {}
    for v in values:
        if v in mapping:
            continue
        found = None
        for c in canon:
            if fuzz.ratio(v, c) >= threshold:
                found = c
                break
        if found is None:
            canon.append(v)
            mapping[v] = v
        else:
            mapping[v] = found
    return mapping

def safe_div(a, b):
    return a / b if b not in (0, 0.0, None) else 0
