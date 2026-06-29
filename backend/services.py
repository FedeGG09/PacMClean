from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from data_quality_evaluator.batch import process_batch_directory
from data_quality_evaluator.checks import run_checks
from data_quality_evaluator.comparison import compare_profiles
from data_quality_evaluator.config import AppConfig
from data_quality_evaluator.io import load_tabular_file, dataframe_to_download_bytes
from data_quality_evaluator.llm import generate_llm_recommendations
from data_quality_evaluator.pii import detect_pii_findings
from data_quality_evaluator.powerbi import publish_dataframe_to_powerbi
from data_quality_evaluator.profiler import profile_dataframe
from data_quality_evaluator.reporting import build_report, report_to_html, report_to_pdf_bytes
from data_quality_evaluator.storage import get_history, init_storage, save_alert, save_cleaning, save_run
from data_quality_evaluator.transformations import apply_transformations, build_action_suggestions

ARTIFACTS_DIR = Path("artifacts")
RUNS_DIR = ARTIFACTS_DIR / "runs"


def _parse_rules_text(rules_text: str | None) -> dict[str, Any]:
    if not rules_text or not rules_text.strip():
        default_rules_path = Path("sample_rules.yaml")
        if default_rules_path.exists():
            from data_quality_evaluator.config import load_rules_file
            return load_rules_file(default_rules_path)
        return {}
    text = rules_text.strip()
    try:
        return json.loads(text)
    except Exception:
        try:
            import yaml
            return yaml.safe_load(text) or {}
        except Exception as e:
            raise ValueError(f"No se pudieron interpretar las reglas: {e}") from e


def _upload_to_df(upload_file) -> tuple[pd.DataFrame, dict[str, Any]]:
    filename = getattr(upload_file, "filename", None) or getattr(upload_file, "name", "uploaded.csv")
    suffix = Path(filename).suffix.lower() or ".csv"
    data = upload_file.file.read() if hasattr(upload_file, "file") else upload_file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    try:
        df, meta = load_tabular_file(tmp_path)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
    return df, meta


def _save_report_artifacts(run_id: int, report: dict[str, Any]) -> dict[str, str]:
    run_dir = RUNS_DIR / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    html_path = run_dir / "report.html"
    pdf_path = run_dir / "report.pdf"
    json_path = run_dir / "report.json"
    html_path.write_text(report_to_html(report), encoding="utf-8")
    pdf_path.write_bytes(report_to_pdf_bytes(report))
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {
        "report_html": f"/api/runs/{run_id}/report.html",
        "report_pdf": f"/api/runs/{run_id}/report.pdf",
        "report_json": f"/api/runs/{run_id}/report.json",
    }


def _analyze_df(
    df: pd.DataFrame,
    source_name: str,
    rules: dict[str, Any],
    cfg: AppConfig,
    use_llm: bool = True,
    llm_model: str | None = None,
    comparison: dict[str, Any] | None = None,
    previous_score: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    profile = profile_dataframe(df, cfg, rules)
    pii_findings = detect_pii_findings(df)
    checks_report = run_checks(df, profile, cfg, rules)
    findings = checks_report["findings"] + pii_findings

    llm_reco = {}
    if use_llm:
        llm_reco = generate_llm_recommendations(
            {
                "source_name": source_name,
                "profile": profile,
                "findings": findings,
                "comparison": comparison,
            },
            model=llm_model,
        )

    actions = build_action_suggestions(df, profile, findings, rules, llm_reco)
    report = build_report(
        df=df,
        profile=profile,
        findings=findings,
        comparison=comparison,
        llm_recommendations=llm_reco,
        llm_derived=None,
        source_name=source_name,
        previous_score=previous_score,
    )
    report["actions"] = actions
    return report, actions, profile, findings


def analyze_upload(
    uploaded_file,
    golden_file=None,
    rules_text: str | None = None,
    use_llm: bool = True,
    compare_previous: bool = True,
    llm_model: str | None = None,
) -> dict[str, Any]:
    init_storage()
    cfg = AppConfig()
    rules = _parse_rules_text(rules_text)
    df, meta = _upload_to_df(uploaded_file)
    source_name = meta["source_name"]

    golden_df = None
    comparison = None
    if golden_file is not None:
        golden_df, _ = _upload_to_df(golden_file)
        golden_profile = profile_dataframe(golden_df, cfg, rules)
        current_profile = profile_dataframe(df, cfg, rules)
        comparison = compare_profiles(current_profile, golden_profile)

    previous_score = None
    if compare_previous:
        history = get_history(limit=1)
        if history:
            previous_score = history[0]["score"]

    report, actions, profile, findings = _analyze_df(
        df=df,
        source_name=source_name,
        rules=rules,
        cfg=cfg,
        use_llm=use_llm,
        llm_model=llm_model,
        comparison=comparison,
        previous_score=previous_score,
    )
    run_id = save_run(report=report, source_name=source_name, input_rows=len(df), input_cols=df.shape[1])
    for alert in report["alerts"]:
        save_alert(run_id, alert)
    urls = _save_report_artifacts(run_id, report)

    return {
        "run_id": run_id,
        "source_name": source_name,
        "summary": report["summary"],
        "executive_summary": report["executive_summary"],
        "alerts": report["alerts"],
        "comparison": report["comparison"],
        "findings": report["findings_display"],
        "actions": actions,
        "data_dictionary": report["data_dictionary"],
        "report_urls": urls,
        "raw_report": report,
        "preview_rows": df.head(20).to_dict(orient="records"),
        "columns": list(df.columns),
    }


def apply_actions_upload(
    uploaded_file,
    selected_action_ids: list[str],
    golden_file=None,
    rules_text: str | None = None,
    use_llm: bool = True,
    compare_previous: bool = True,
    llm_model: str | None = None,
) -> dict[str, Any]:
    init_storage()
    cfg = AppConfig()
    rules = _parse_rules_text(rules_text)
    df, meta = _upload_to_df(uploaded_file)
    source_name = meta["source_name"]

    golden_df = None
    comparison = None
    if golden_file is not None:
        golden_df, _ = _upload_to_df(golden_file)
        golden_profile = profile_dataframe(golden_df, cfg, rules)
        current_profile = profile_dataframe(df, cfg, rules)
        comparison = compare_profiles(current_profile, golden_profile)

    previous_score = None
    if compare_previous:
        history = get_history(limit=1)
        if history:
            previous_score = history[0]["score"]

    before_report, actions, profile, findings = _analyze_df(
        df=df,
        source_name=source_name,
        rules=rules,
        cfg=cfg,
        use_llm=use_llm,
        llm_model=llm_model,
        comparison=comparison,
        previous_score=previous_score,
    )

    cleaned_df, applied = apply_transformations(df, actions, selected_action_ids)

    # Rebuild comparison after cleaning, if applicable
    cleaned_comparison = None
    if golden_df is not None:
        cleaned_profile = profile_dataframe(cleaned_df, cfg, rules)
        golden_profile = profile_dataframe(golden_df, cfg, rules)
        cleaned_comparison = compare_profiles(cleaned_profile, golden_profile)

    cleaned_report, _, _, _ = _analyze_df(
        df=cleaned_df,
        source_name=f"{source_name} (cleaned)",
        rules=rules,
        cfg=cfg,
        use_llm=use_llm,
        llm_model=llm_model,
        comparison=cleaned_comparison,
        previous_score=before_report["summary"]["quality_score"],
    )

    run_id = save_run(report=cleaned_report, source_name=source_name, input_rows=len(df), input_cols=df.shape[1])
    for alert in cleaned_report["alerts"]:
        save_alert(run_id, alert)

    run_dir = RUNS_DIR / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "cleaned.csv"
    xlsx_path = run_dir / "cleaned.xlsx"
    csv_path.write_bytes(dataframe_to_download_bytes(cleaned_df, source_name, format="csv"))
    xlsx_path.write_bytes(dataframe_to_download_bytes(cleaned_df, source_name, format="xlsx"))
    save_cleaning(run_id, str(csv_path), actions=applied, derived=[])

    urls = _save_report_artifacts(run_id, cleaned_report)

    csv_url = f"/api/runs/{run_id}/cleaned.csv"
    xlsx_url = f"/api/runs/{run_id}/cleaned.xlsx"
    csv_path = RUNS_DIR / str(run_id) / "cleaned.csv"
    xlsx_path = RUNS_DIR / str(run_id) / "cleaned.xlsx"

    return {
        "run_id": run_id,
        "source_name": source_name,
        "before_summary": before_report["summary"],
        "after_summary": cleaned_report["summary"],
        "before_alerts": before_report["alerts"],
        "after_alerts": cleaned_report["alerts"],
        "before_findings": before_report["findings_display"],
        "after_findings": cleaned_report["findings_display"],
        "comparison_before": before_report["comparison"],
        "comparison_after": cleaned_report["comparison"],
        "applied_actions": applied,
        "selected_action_ids": selected_action_ids,
        "cleaned_preview": cleaned_df.head(20).to_dict(orient="records"),
        "artifact_paths": {
            "cleaned_csv": str(csv_path),
            "cleaned_xlsx": str(xlsx_path),
            "report_html": str(RUNS_DIR / str(run_id) / "report.html"),
            "report_pdf": str(RUNS_DIR / str(run_id) / "report.pdf"),
            "report_json": str(RUNS_DIR / str(run_id) / "report.json"),
        },
        "download_urls": {
            **urls,
            "cleaned_csv": csv_url,
            "cleaned_xlsx": xlsx_url,
        },
        "raw_report": cleaned_report,
        "columns": list(cleaned_df.columns),
    }


def export_to_powerbi_upload(
    uploaded_file,
    selected_action_ids: list[str],
    golden_file=None,
    rules_text: str | None = None,
    use_llm: bool = True,
    compare_previous: bool = True,
    llm_model: str | None = None,
    powerbi_token: str | None = None,
    dataset_name: str = "EvaluadorCalidadDatos",
    table_name: str = "clean_data",
) -> dict[str, Any]:
    result = apply_actions_upload(
        uploaded_file=uploaded_file,
        selected_action_ids=selected_action_ids,
        golden_file=golden_file,
        rules_text=rules_text,
        use_llm=use_llm,
        compare_previous=compare_previous,
        llm_model=llm_model,
    )
    # Re-load cleaned file from the saved CSV so that Power BI export matches the downloadable artifact
    cleaned_csv = Path(result["artifact_paths"]["cleaned_csv"])
    if not cleaned_csv.exists():
        raise FileNotFoundError("No se encontró el archivo limpio para exportar a Power BI.")
    cleaned_df = pd.read_csv(cleaned_csv)
    pb = publish_dataframe_to_powerbi(
        df=cleaned_df,
        token=powerbi_token,
        dataset_name=dataset_name,
        table_name=table_name,
    )
    result["powerbi"] = pb
    return result


def batch_process(input_dir: str, output_dir: str | None, rules_text: str | None = None, llm_model: str | None = None) -> dict[str, Any]:
    cfg = AppConfig()
    rules = _parse_rules_text(rules_text)
    result = process_batch_directory(Path(input_dir), cfg, rules, llm_model=llm_model, output_dir=Path(output_dir) if output_dir else None)
    return result
