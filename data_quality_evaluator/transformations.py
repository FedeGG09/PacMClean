from __future__ import annotations
from typing import Any
import pandas as pd
from .utils import normalize_text, normalize_key, parse_dates, iqr_outlier_mask, fuzzy_canonical_map

def build_action_suggestions(df: pd.DataFrame, profile: dict, findings: list[dict], rules: dict[str, Any], llm_reco: dict[str, Any] | None = None):
    actions = []
    seen = set()
    for f in findings:
        sug = f.get("suggested_action")
        if not sug:
            continue
        action_type = sug.get("action_type")
        params = sug.get("parameters", {})
        aid = f"{action_type}:{params}"
        if aid in seen:
            continue
        seen.add(aid)
        col = params.get("column") or f.get("column")
        preview = build_preview(df, action_type, params)
        est = estimate_impact(df, action_type, params)
        actions.append({
            "id": aid,
            "title": human_title(action_type, col),
            "description": human_description(action_type, f),
            "action_type": action_type,
            "parameters": params,
            "risk_level": risk_level(action_type),
            "estimated_affected_rows": est,
            "preview": preview,
        })
    for col in df.columns:
        if df[col].dtype == "object":
            aid = f"trim_whitespace:{col}"
            if aid not in seen and df[col].astype(str).str.contains(r"^\s+|\s+$", regex=True, na=False).any():
                actions.append({
                    "id": aid,
                    "title": f"Recortar espacios en '{col}'",
                    "description": "Elimina espacios iniciales/finales.",
                    "action_type": "trim_whitespace",
                    "parameters": {"column": col},
                    "risk_level": "low",
                    "estimated_affected_rows": int(df[col].astype(str).str.contains(r"^\s+|\s+$", regex=True, na=False).sum()),
                    "preview": build_preview(df, "trim_whitespace", {"column": col}),
                })
    return actions

def human_title(action_type, col):
    mapping = {
        "drop_duplicates": "Eliminar duplicados",
        "clip_outliers": f"Limitar outliers en '{col}'",
        "parse_dates": f"Parsear fechas en '{col}'",
        "normalize_categories": f"Normalizar categorías en '{col}'",
        "impute_or_drop": f"Revisar nulos en '{col}'",
        "mask_pii": f"Enmascarar PII en '{col}'",
        "clip_or_review": f"Revisar rangos en '{col}'",
        "normalize_or_review": f"Normalizar valores en '{col}'",
        "review_date_order": "Revisar orden de fechas",
        "review_total_sum": "Revisar suma de totales",
        "add_missing_column": "Agregar columna faltante",
    }
    return mapping.get(action_type, f"Acción {action_type}")

def human_description(action_type, finding):
    return finding.get("message", "Acción sugerida.")

def risk_level(action_type):
    low = {"trim_whitespace", "mask_pii"}
    med = {"normalize_categories", "parse_dates", "clip_outliers", "normalize_or_review", "clip_or_review"}
    high = {"drop_duplicates", "impute_or_drop", "review_date_order", "review_total_sum", "add_missing_column"}
    if action_type in low:
        return "low"
    if action_type in med:
        return "medium"
    return "high"

def estimate_impact(df, action_type, params):
    col = params.get("column")
    if action_type == "trim_whitespace" and col in df.columns:
        return int(df[col].astype(str).str.contains(r"^\s+|\s+$", regex=True, na=False).sum())
    if action_type == "drop_duplicates":
        return int(df.duplicated(keep=False).sum())
    if action_type == "mask_pii" and col in df.columns:
        return int(df[col].notna().sum())
    if col in df.columns and action_type in {"clip_outliers", "parse_dates", "normalize_categories", "clip_or_review", "normalize_or_review"}:
        return int(df[col].notna().sum())
    return 0

def build_preview(df, action_type, params, n=5):
    col = params.get("column")
    if action_type == "trim_whitespace" and col in df.columns:
        before = df[col].head(n).tolist()
        after = df[col].astype(str).str.strip().head(n).tolist()
        return {"before": before, "after": after}
    if action_type == "drop_duplicates":
        return {"rows_to_drop": int(df.duplicated(keep="first").sum())}
    if action_type == "normalize_categories" and col in df.columns:
        vals = df[col].dropna().astype(str)
        mapping = fuzzy_canonical_map(vals.unique().tolist())
        return {"mapping_sample": dict(list(mapping.items())[:10])}
    if action_type == "parse_dates" and col in df.columns:
        parsed = parse_dates(df[col]).head(n).astype(str).tolist()
        return {"parsed_sample": parsed}
    if action_type == "clip_outliers" and col in df.columns:
        num = pd.to_numeric(df[col], errors="coerce")
        mask = iqr_outlier_mask(num)
        return {"outlier_rows": df.loc[mask, [col]].head(n).to_dict(orient="records")}
    return {"note": "Preview no disponible"}

def apply_transformations(df: pd.DataFrame, action_suggestions: list[dict], selected_action_ids: list[str]):
    applied = []
    out = df.copy()
    for action in action_suggestions:
        if action["id"] not in selected_action_ids:
            continue
        before_rows = len(out)
        out = _apply_action(out, action)
        after_rows = len(out)
        applied.append({
            "id": action["id"],
            "title": action["title"],
            "action_type": action["action_type"],
            "parameters": action["parameters"],
            "rows_before": before_rows,
            "rows_after": after_rows,
        })
    return out, applied

def _apply_action(df: pd.DataFrame, action: dict):
    at = action["action_type"]
    p = action["parameters"]
    col = p.get("column")
    if at == "trim_whitespace" and col in df.columns:
        df[col] = df[col].astype(str).str.strip()
    elif at == "drop_duplicates":
        df = df.drop_duplicates(keep="first").reset_index(drop=True)
    elif at == "normalize_categories" and col in df.columns:
        df[col] = df[col].astype(str).map(normalize_key)
    elif at == "parse_dates" and col in df.columns:
        df[col] = parse_dates(df[col])
    elif at == "clip_outliers" and col in df.columns:
        num = pd.to_numeric(df[col], errors="coerce")
        mask = iqr_outlier_mask(num)
        lower = num[~mask].quantile(0.01) if (~mask).any() else num.quantile(0.01)
        upper = num[~mask].quantile(0.99) if (~mask).any() else num.quantile(0.99)
        df[col] = num.clip(lower, upper)
    elif at == "mask_pii" and col in df.columns:
        from .pii import mask_pii_dataframe
        df = mask_pii_dataframe(df, [col])
    return df
