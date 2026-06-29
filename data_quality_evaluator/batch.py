from __future__ import annotations
from pathlib import Path
from typing import Any
from .io import load_tabular_file
from .profiler import profile_dataframe
from .checks import run_checks
from .pii import detect_pii_findings
from .reporting import build_report, report_to_html
from .llm import generate_llm_recommendations

def process_batch_directory(input_dir: Path, cfg, rules: dict[str, Any], llm_model: str | None = None, output_dir: Path | None = None):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir or input_dir / "batch_output")
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    files_processed = 0
    for p in input_dir.glob("*"):
        if p.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue
        try:
            df, meta = load_tabular_file(p)
            profile = profile_dataframe(df, cfg, rules)
            findings = run_checks(df, profile, cfg, rules)["findings"] + detect_pii_findings(df)
            llm_reco = generate_llm_recommendations({"profile": profile, "findings": findings}, model=llm_model)
            report = build_report(df, profile, findings, None, llm_reco, None, meta["source_name"])
            html = report_to_html(report)
            (output_dir / f"{p.stem}_report.html").write_text(html, encoding="utf-8")
            results.append({
                "file": p.name,
                "rows": len(df),
                "cols": df.shape[1],
                "score": report["summary"]["quality_score"],
                "report": str(output_dir / f"{p.stem}_report.html")
            })
            files_processed += 1
        except Exception as e:
            results.append({"file": p.name, "error": str(e)})
    return {"summary": {"files_processed": files_processed}, "files": results, "output_dir": str(output_dir)}
