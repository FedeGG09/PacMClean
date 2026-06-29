from __future__ import annotations
from typing import Any
import io
import json
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from .utils import safe_json


def _scalar_display(value):
    if value is None:
        return None
    if isinstance(value, (dict, list, tuple, set)):
        return json.dumps(safe_json(value), ensure_ascii=False)
    return str(value) if not isinstance(value, (str, int, float, bool)) else value

def build_data_dictionary(df: pd.DataFrame, profile: dict):
    rows = []
    for col, p in profile["profiles"].items():
        rows.append({
            "column": col,
            "inferred_type": profile["inferred_schema"].get(col, "unknown"),
            "raw_dtype": p["dtype_raw"],
            "null_pct": p["null_pct"],
            "n_unique": p["n_unique"],
            "top_values": ", ".join([str(x["value"]) for x in p["top_values"][:3]]),
            "samples": ", ".join(map(str, p["sample_values"][:3])),
        })
    return rows

def compute_quality_score(findings: list[dict], profile: dict, cfg=None, comparison=None):
    score = 100.0
    weights = getattr(cfg, "quality_weights", {}) if cfg else {}
    for f in findings:
        t = f.get("type", "")
        sev = f.get("severity", "medium")
        base = {"high": 1.0, "medium": 0.6, "low": 0.3}.get(sev, 0.6)
        if "missing" in t:
            score -= weights.get("missing", 25) * base / 5
        elif "duplicate" in t:
            score -= weights.get("duplicates", 15) * base / 5
        elif "outlier" in t:
            score -= weights.get("outliers", 10) * base / 5
        elif "date" in t:
            score -= weights.get("invalid_dates", 15) * base / 5
        elif "typo" in t:
            score -= weights.get("typos", 10) * base / 5
        elif "pii" in t:
            score -= weights.get("pii", 10) * base / 5
        elif "cross_column" in t:
            score -= weights.get("cross_checks", 15) * base / 5
        elif "range" in t or "regex" in t:
            score -= 3 * base
    if comparison:
        drift = comparison.get("schema_drift", {})
        score -= min(10, len(drift.get("missing_columns", [])) * 2)
        score -= min(10, len(drift.get("type_changes", [])) * 2)
    return max(0, round(score))

def build_alerts(findings, comparison, score, cfg=None, previous_score=None):
    alerts = []
    if comparison and comparison.get("schema_drift", {}).get("missing_columns"):
        alerts.append("Drift de schema: faltan columnas respecto a la referencia.")
    if comparison and comparison.get("schema_drift", {}).get("extra_columns"):
        alerts.append("Drift de schema: aparecen columnas nuevas respecto a la referencia.")
    if previous_score is not None and score < previous_score:
        alerts.append(f"Degradación de calidad: el score bajó de {previous_score} a {score}.")
    if score < 75:
        alerts.append("La calidad general está por debajo del umbral recomendado.")
    for f in findings:
        if f.get("severity") == "high" and f.get("type") in {"pii_detected", "critical_missing_values", "critical_missing_column"}:
            alerts.append(f"Alerta alta: {f.get('message')}")
    return alerts

def build_report(df, profile, findings, comparison, llm_recommendations=None, llm_derived=None, source_name="", previous_score=None):
    findings_display = []
    for f in findings:
        ex = f.get("examples")
        if ex is not None:
            try:
                examples_text = json.dumps(safe_json(ex), ensure_ascii=False)
            except Exception:
                examples_text = str(ex)
        else:
            examples_text = None
        findings_display.append({
            "id": f.get("id"),
            "type": f.get("type"),
            "severity": f.get("severity"),
            "column": f.get("column") or ", ".join(f.get("columns", [])),
            "count": f.get("count"),
            "metric": f.get("metric"),
            "message": f.get("message"),
            "examples": examples_text,
        })
    data_dictionary = build_data_dictionary(df, profile)
    from .config import AppConfig
    score = compute_quality_score(findings, profile, AppConfig(), comparison)
    alerts = build_alerts(findings, comparison, score, previous_score=previous_score)
    executive_summary = (
        llm_recommendations.get("executive_summary")
        if isinstance(llm_recommendations, dict) and llm_recommendations.get("executive_summary")
        else f"La base '{source_name}' fue analizada con {len(findings)} hallazgos. Score de calidad: {score}/100."
    )
    return {
        "source_name": source_name,
        "summary": {"rows": int(len(df)), "cols": int(df.shape[1]), "quality_score": score},
        "executive_summary": executive_summary,
        "findings": safe_json(findings),
        "findings_display": findings_display,
        "comparison": safe_json(comparison),
        "data_dictionary": data_dictionary,
        "llm_recommendations": safe_json(llm_recommendations),
        "llm_derived": safe_json(llm_derived),
        "alerts": alerts,
    }

def report_to_html(report: dict[str, Any]) -> str:
    findings_rows = "".join(
        f"<tr><td>{f.get('type')}</td><td>{f.get('column')}</td><td>{f.get('severity')}</td><td>{f.get('message')}</td></tr>"
        for f in report["findings_display"]
    )
    data_dict_rows = "".join(
        f"<tr><td>{d['column']}</td><td>{d['inferred_type']}</td><td>{d['null_pct']}</td><td>{d['n_unique']}</td></tr>"
        for d in report["data_dictionary"]
    )
    return f"""
    <html>
    <head><meta charset="utf-8"><style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; font-size: 12px; }}
    th {{ background: #f4f4f4; }}
    .score {{ font-size: 22px; font-weight: bold; }}
    </style></head>
    <body>
    <h1>Reporte de Calidad de Datos</h1>
    <div class="score">Score: {report['summary']['quality_score']}/100</div>
    <p>{report['executive_summary']}</p>
    <h2>Hallazgos</h2>
    <table><tr><th>Tipo</th><th>Columna</th><th>Severidad</th><th>Detalle</th></tr>{findings_rows}</table>
    <h2>Diccionario de datos</h2>
    <table><tr><th>Columna</th><th>Tipo</th><th>% Nulos</th><th>Únicos</th></tr>{data_dict_rows}</table>
    </body>
    </html>
    """

def report_to_pdf_bytes(report: dict[str, Any]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("Reporte de Calidad de Datos", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Score: {report['summary']['quality_score']}/100", styles["Heading2"]))
    story.append(Paragraph(report["executive_summary"], styles["BodyText"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Hallazgos", styles["Heading2"]))
    table_data = [["Tipo", "Columna", "Severidad", "Detalle"]]
    for f in report["findings_display"]:
        table_data.append([str(f.get("type")), str(f.get("column")), str(f.get("severity")), str(f.get("message"))])
    tbl = Table(table_data, colWidths=[100, 100, 70, 260])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 12))
    story.append(Paragraph("Diccionario de datos", styles["Heading2"]))
    dd = [["Columna", "Tipo", "% Nulos", "Únicos"]]
    for d in report["data_dictionary"]:
        dd.append([d["column"], d["inferred_type"], str(d["null_pct"]), str(d["n_unique"])])
    tbl2 = Table(dd, colWidths=[140, 130, 70, 70])
    tbl2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(tbl2)
    doc.build(story)
    return buffer.getvalue()
