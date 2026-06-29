from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from backend.services import (
    analyze_upload,
    apply_actions_upload,
    batch_process,
    export_to_powerbi_upload,
)
from data_quality_evaluator.storage import init_storage, get_history

app = FastAPI(
    title="Evaluador de Calidad de Datos API",
    version="1.0.0",
)

# CORS para desarrollo local, localhost, 127.0.0.1 e IPs de red tipo 192.168.x.x
# Esto evita "Failed to fetch" cuando el front corre en Vite y abre network URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3})(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_storage()

ARTIFACTS_DIR = Path("artifacts")
RUNS_DIR = ARTIFACTS_DIR / "runs"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/history")
def api_history(limit: int = 50):
    return {"items": get_history(limit=limit)}


def _parse_action_ids(text: str | None) -> list[str]:
    if not text:
        return []
    try:
        val = json.loads(text)
        if isinstance(val, list):
            return [str(x) for x in val]
    except Exception:
        pass
    return [x.strip() for x in text.split(",") if x.strip()]


@app.post("/api/analyze")
async def api_analyze(
    file: UploadFile = File(...),
    golden_file: UploadFile | None = File(None),
    rules_text: str = Form(""),
    use_llm: bool = Form(True),
    compare_previous: bool = Form(True),
    llm_model: Optional[str] = Form(None),
):
    try:
        result = analyze_upload(
            uploaded_file=file,
            golden_file=golden_file,
            rules_text=rules_text,
            use_llm=use_llm,
            compare_previous=compare_previous,
            llm_model=llm_model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/apply-actions")
async def api_apply_actions(
    file: UploadFile = File(...),
    selected_action_ids: str = Form("[]"),
    golden_file: UploadFile | None = File(None),
    rules_text: str = Form(""),
    use_llm: bool = Form(True),
    compare_previous: bool = Form(True),
    llm_model: Optional[str] = Form(None),
):
    try:
        action_ids = _parse_action_ids(selected_action_ids)
        result = apply_actions_upload(
            uploaded_file=file,
            selected_action_ids=action_ids,
            golden_file=golden_file,
            rules_text=rules_text,
            use_llm=use_llm,
            compare_previous=compare_previous,
            llm_model=llm_model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/export/powerbi")
async def api_export_powerbi(
    file: UploadFile = File(...),
    selected_action_ids: str = Form("[]"),
    golden_file: UploadFile | None = File(None),
    rules_text: str = Form(""),
    use_llm: bool = Form(True),
    compare_previous: bool = Form(True),
    llm_model: Optional[str] = Form(None),
    powerbi_token: Optional[str] = Form(None),
    dataset_name: str = Form("EvaluadorCalidadDatos"),
    table_name: str = Form("clean_data"),
):
    try:
        action_ids = _parse_action_ids(selected_action_ids)
        result = export_to_powerbi_upload(
            uploaded_file=file,
            selected_action_ids=action_ids,
            golden_file=golden_file,
            rules_text=rules_text,
            use_llm=use_llm,
            compare_previous=compare_previous,
            llm_model=llm_model,
            powerbi_token=powerbi_token,
            dataset_name=dataset_name,
            table_name=table_name,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/batch")
async def api_batch(
    input_dir: str = Form(...),
    output_dir: str = Form("artifacts/batch_output"),
    rules_text: str = Form(""),
    llm_model: Optional[str] = Form(None),
):
    try:
        result = batch_process(
            input_dir=input_dir,
            output_dir=output_dir,
            rules_text=rules_text,
            llm_model=llm_model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/runs/{run_id}/report.html")
def get_report_html(run_id: int):
    path = RUNS_DIR / str(run_id) / "report.html"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reporte HTML no encontrado.")
    return FileResponse(path, media_type="text/html", filename=path.name)


@app.get("/api/runs/{run_id}/report.pdf")
def get_report_pdf(run_id: int):
    path = RUNS_DIR / str(run_id) / "report.pdf"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reporte PDF no encontrado.")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@app.get("/api/runs/{run_id}/report.json")
def get_report_json(run_id: int):
    path = RUNS_DIR / str(run_id) / "report.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Reporte JSON no encontrado.")
    return FileResponse(path, media_type="application/json", filename=path.name)


@app.get("/api/runs/{run_id}/cleaned.csv")
def get_cleaned_csv(run_id: int):
    path = RUNS_DIR / str(run_id) / "cleaned.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo CSV limpio no encontrado.")
    return FileResponse(path, media_type="text/csv", filename=path.name)


@app.get("/api/runs/{run_id}/cleaned.xlsx")
def get_cleaned_xlsx(run_id: int):
    path = RUNS_DIR / str(run_id) / "cleaned.xlsx"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo XLSX limpio no encontrado.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=path.name,
    )


@app.get("/")
def root():
    return {
        "message": "Evaluador de Calidad de Datos API",
        "docs": "/docs",
        "health": "/api/health",
    }