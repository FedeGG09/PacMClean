from __future__ import annotations
from typing import Any
import re
import pandas as pd
import numpy as np
from .utils import iqr_outlier_mask, parse_dates, normalize_key, safe_div

def detect_missing_values(df: pd.DataFrame, cfg, rules):
    findings = []
    for col in df.columns:
        pct = df[col].isna().mean()
        if pct >= cfg.null_medium_threshold:
            sev = "high" if pct >= cfg.null_high_threshold else "medium"
            findings.append({
                "id": f"missing_{col}",
                "type": "missing_values",
                "severity": sev,
                "column": col,
                "metric": round(pct * 100, 2),
                "message": f"La columna '{col}' tiene {round(pct*100,2)}% de nulos.",
                "examples": df.loc[df[col].isna(), col].head(5).tolist(),
                "suggested_action": {
                    "action_type": "impute_or_drop",
                    "parameters": {"column": col, "strategy": "review"}
                }
            })
    return findings

def detect_duplicates(df: pd.DataFrame, cfg, rules):
    findings = []
    dup_mask = df.duplicated(keep=False)
    dup_count = int(dup_mask.sum())
    if dup_count:
        findings.append({
            "id": "duplicates_exact",
            "type": "duplicates",
            "severity": "high" if safe_div(dup_count, len(df)) >= cfg.duplicate_high_threshold else "medium",
            "metric": round(safe_div(dup_count, len(df)) * 100, 2),
            "count": dup_count,
            "message": f"Se detectaron {dup_count} filas duplicadas exactas.",
            "examples": df.loc[dup_mask].head(5).to_dict(orient="records"),
            "suggested_action": {
                "action_type": "drop_duplicates",
                "parameters": {"keep": "first"}
            }
        })
    return findings

def detect_numeric_outliers(df: pd.DataFrame, profile: dict, cfg, rules):
    findings = []
    for col, p in profile["profiles"].items():
        if p["is_numeric_candidate"] and not p["is_boolean_like"] and not p["is_date_candidate"]:
            num = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
            mask = iqr_outlier_mask(num, multiplier=cfg.outlier_iqr_multiplier)
            count = int(mask.sum())
            if count:
                findings.append({
                    "id": f"outliers_{col}",
                    "type": "outliers",
                    "severity": "medium",
                    "column": col,
                    "count": count,
                    "metric": round(safe_div(count, len(df)) * 100, 2),
                    "message": f"Se detectaron {count} outliers en '{col}'.",
                    "examples": df.loc[mask, [col]].head(5).to_dict(orient="records"),
                    "suggested_action": {
                        "action_type": "clip_outliers",
                        "parameters": {"column": col, "method": "iqr"}
                    }
                })
    return findings

def detect_invalid_dates(df: pd.DataFrame, profile: dict, cfg, rules):
    findings = []
    for col, p in profile["profiles"].items():
        if p["is_date_candidate"]:
            parsed = parse_dates(df[col])
            invalid = parsed.isna() & df[col].notna()
            count = int(invalid.sum())
            if count:
                findings.append({
                    "id": f"invalid_dates_{col}",
                    "type": "invalid_dates",
                    "severity": "high",
                    "column": col,
                    "count": count,
                    "metric": round(safe_div(count, len(df)) * 100, 2),
                    "message": f"Se detectaron {count} fechas inválidas en '{col}'.",
                    "examples": df.loc[invalid, [col]].head(5).to_dict(orient="records"),
                    "suggested_action": {
                        "action_type": "parse_dates",
                        "parameters": {"column": col, "errors": "coerce"}
                    }
                })
    return findings

def detect_category_typos(df: pd.DataFrame, profile: dict, cfg, rules):
    findings = []
    for col, p in profile["profiles"].items():
        if p["is_numeric_candidate"] or p["is_date_candidate"] or p["is_boolean_like"]:
            continue
        s = df[col].dropna().astype(str).map(normalize_key)
        if s.nunique() < 2:
            continue
        value_counts = s.value_counts()
        if len(value_counts) >= 3:
            max_pct = value_counts.iloc[0] / len(s)
            if max_pct >= 0.5:
                rare = value_counts[value_counts <= 2]
                if len(rare):
                    findings.append({
                        "id": f"typos_{col}",
                        "type": "category_typos",
                        "severity": "medium",
                        "column": col,
                        "count": int(rare.sum()),
                        "message": f"Hay variantes raras o posibles typos en '{col}'.",
                        "examples": rare.head(5).index.tolist(),
                        "suggested_action": {
                            "action_type": "normalize_categories",
                            "parameters": {"column": col, "mode": "fuzzy"}
                        }
                    })
    return findings

def detect_critical_missing(df: pd.DataFrame, rules):
    findings = []
    required = rules.get("required_columns", [])
    for col in required:
        if col not in df.columns:
            findings.append({
                "id": f"missing_required_{col}",
                "type": "critical_missing_column",
                "severity": "high",
                "column": col,
                "message": f"Falta la columna obligatoria '{col}'.",
                "suggested_action": {"action_type": "add_missing_column", "parameters": {"column": col}}
            })
        else:
            pct = df[col].isna().mean()
            if pct > 0:
                findings.append({
                    "id": f"critical_missing_{col}",
                    "type": "critical_missing_values",
                    "severity": "high" if pct >= 0.05 else "medium",
                    "column": col,
                    "metric": round(pct * 100, 2),
                    "message": f"La columna obligatoria '{col}' tiene nulos.",
                    "examples": df.loc[df[col].isna(), [col]].head(5).to_dict(orient="records"),
                    "suggested_action": {
                        "action_type": "review_required_field",
                        "parameters": {"column": col}
                    }
                })
    return findings

def detect_rule_violations(df: pd.DataFrame, rules):
    findings = []
    ranges = rules.get("numeric_ranges", {})
    for col, bounds in ranges.items():
        if col in df.columns:
            num = pd.to_numeric(df[col], errors="coerce")
            invalid = pd.Series(False, index=df.index)
            if "min" in bounds:
                invalid = invalid | (num < bounds["min"])
            if "max" in bounds:
                invalid = invalid | (num > bounds["max"])
            count = int(invalid.fillna(False).sum())
            if count:
                findings.append({
                    "id": f"range_{col}",
                    "type": "numeric_range_violation",
                    "severity": "high",
                    "column": col,
                    "count": count,
                    "message": f"'{col}' viola el rango configurado.",
                    "examples": df.loc[invalid, [col]].head(5).to_dict(orient="records"),
                    "suggested_action": {"action_type": "clip_or_review", "parameters": {"column": col}}
                })
    regex_rules = rules.get("regex_rules", {})
    for col, spec in regex_rules.items():
        pattern = spec.get("pattern")
        if col in df.columns and pattern:
            mask = df[col].astype(str).map(lambda x: bool(re.match(pattern, x.strip())) if pd.notna(x) else False)
            invalid = ~mask & df[col].notna()
            count = int(invalid.sum())
            if count:
                findings.append({
                    "id": f"regex_{col}",
                    "type": "regex_violation",
                    "severity": "medium",
                    "column": col,
                    "count": count,
                    "message": f"'{col}' no cumple la expresión regular configurada.",
                    "examples": df.loc[invalid, [col]].head(5).to_dict(orient="records"),
                    "suggested_action": {"action_type": "normalize_or_review", "parameters": {"column": col}}
                })
    return findings

def detect_cross_column_issues(df: pd.DataFrame, profile: dict, rules: dict[str, Any]):
    findings = []
    for rule in rules.get("cross_column_rules", []):
        if rule.get("type") == "date_order":
            start, end = rule.get("start"), rule.get("end")
            if start in df.columns and end in df.columns:
                s1 = parse_dates(df[start])
                s2 = parse_dates(df[end])
                invalid = s2.notna() & s1.notna() & (s2 < s1)
                count = int(invalid.sum())
                if count:
                    findings.append({
                        "id": f"date_order_{start}_{end}",
                        "type": "cross_column_date_order",
                        "severity": rule.get("severity", "high"),
                        "columns": [start, end],
                        "count": count,
                        "message": f"Se detectó {count} veces que '{end}' es menor que '{start}'.",
                        "examples": df.loc[invalid, [start, end]].head(5).to_dict(orient="records"),
                        "suggested_action": {"action_type": "review_date_order", "parameters": {"start": start, "end": end}}
                    })
        elif rule.get("type") == "total_equals_sum":
            total = rule.get("total")
            parts = rule.get("parts", [])
            tol = float(rule.get("tolerance", 0.0))
            if total in df.columns and all(p in df.columns for p in parts):
                total_s = pd.to_numeric(df[total], errors="coerce")
                parts_s = sum(pd.to_numeric(df[p], errors="coerce").fillna(0) for p in parts)
                invalid = total_s.notna() & (abs(total_s - parts_s) > tol)
                count = int(invalid.sum())
                if count:
                    findings.append({
                        "id": f"total_sum_{total}",
                        "type": "cross_column_total_sum",
                        "severity": rule.get("severity", "medium"),
                        "columns": [total] + parts,
                        "count": count,
                        "message": f"'{total}' no coincide con la suma de sus partes.",
                        "examples": df.loc[invalid, [total] + parts].head(5).to_dict(orient="records"),
                        "suggested_action": {"action_type": "review_total_sum", "parameters": {"total": total, "parts": parts}}
                    })

    date_cols = [c for c, p in profile["profiles"].items() if p["is_date_candidate"]]
    for a in date_cols:
        la = a.lower()
        if any(w in la for w in ["inicio", "start", "desde", "begin"]):
            for b in date_cols:
                lb = b.lower()
                if any(w in lb for w in ["fin", "end", "hasta", "finish"]):
                    s1 = parse_dates(df[a]); s2 = parse_dates(df[b])
                    invalid = s1.notna() & s2.notna() & (s2 < s1)
                    count = int(invalid.sum())
                    if count:
                        findings.append({
                            "id": f"heuristic_date_order_{a}_{b}",
                            "type": "cross_column_date_order",
                            "severity": "high",
                            "columns": [a, b],
                            "count": count,
                            "message": f"Posible inconsistencia lógica: '{b}' < '{a}'.",
                            "examples": df.loc[invalid, [a, b]].head(5).to_dict(orient="records"),
                            "suggested_action": {"action_type": "review_date_order", "parameters": {"start": a, "end": b}}
                        })
    return findings

def run_checks(df: pd.DataFrame, profile: dict, cfg, rules: dict[str, Any]):
    findings = []
    findings.extend(detect_missing_values(df, cfg, rules))
    findings.extend(detect_duplicates(df, cfg, rules))
    findings.extend(detect_numeric_outliers(df, profile, cfg, rules))
    findings.extend(detect_invalid_dates(df, profile, cfg, rules))
    findings.extend(detect_category_typos(df, profile, cfg, rules))
    findings.extend(detect_critical_missing(df, rules))
    findings.extend(detect_rule_violations(df, rules))
    findings.extend(detect_cross_column_issues(df, profile, rules))
    return {"findings": findings}
