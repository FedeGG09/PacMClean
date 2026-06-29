import argparse
from pathlib import Path

from data_quality_evaluator.config import AppConfig, load_rules_file
from data_quality_evaluator.io import load_tabular_file
from data_quality_evaluator.profiler import profile_dataframe
from data_quality_evaluator.checks import run_checks
from data_quality_evaluator.pii import detect_pii_findings
from data_quality_evaluator.reporting import build_report, report_to_html, report_to_pdf_bytes
from data_quality_evaluator.llm import generate_llm_recommendations
from data_quality_evaluator.batch import process_batch_directory

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_an = sub.add_parser("analyze")
    p_an.add_argument("--file", required=True)
    p_an.add_argument("--rules", default="sample_rules.yaml")
    p_an.add_argument("--outdir", default="artifacts")

    p_batch = sub.add_parser("batch")
    p_batch.add_argument("--input-dir", required=True)
    p_batch.add_argument("--output-dir", required=True)
    p_batch.add_argument("--rules", default="sample_rules.yaml")

    args = parser.parse_args()
    cfg = AppConfig()
    rules = load_rules_file(args.rules) if Path(args.rules).exists() else {}

    if args.cmd == "analyze":
        df, meta = load_tabular_file(args.file)
        profile = profile_dataframe(df, cfg, rules)
        findings = run_checks(df, profile, cfg, rules)["findings"] + detect_pii_findings(df)
        llm_reco = generate_llm_recommendations({"profile": profile, "findings": findings}, model=None)
        report = build_report(df, profile, findings, None, llm_reco, None, meta["source_name"])
        outdir = Path(args.outdir)
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "report.html").write_text(report_to_html(report), encoding="utf-8")
        (outdir / "report.pdf").write_bytes(report_to_pdf_bytes(report))
        print(report["executive_summary"])
        print(f"HTML: {outdir / 'report.html'}")
        print(f"PDF: {outdir / 'report.pdf'}")
    elif args.cmd == "batch":
        result = process_batch_directory(Path(args.input_dir), cfg, rules, llm_model=None, output_dir=Path(args.output_dir))
        print(result["summary"])

if __name__ == "__main__":
    main()
