from __future__ import annotations
import os
import json
from typing import Any
from .utils import safe_json

def _client():
    try:
        from openai import OpenAI
    except Exception:
        return None
    base = os.getenv("OPENAI_API_BASE", "http://127.0.0.1:1234/v1")
    key = os.getenv("OPENAI_API_KEY", "lm-studio")
    try:
        return OpenAI(base_url=base, api_key=key)
    except Exception:
        return None

def generate_llm_recommendations(bundle: dict[str, Any], model: str | None = None):
    client = _client()
    if client is None:
        return {}
    model = model or os.getenv("LMSTUDIO_MODEL", "")
    if not model:
        return {}
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Eres un analista de calidad de datos. Solo redactas recomendaciones basadas en el JSON provisto. No inventes hallazgos."},
                {"role": "user", "content": json.dumps(safe_json(bundle), ensure_ascii=False, indent=2)},
            ],
            temperature=0.2,
        )
        content = resp.choices[0].message.content or ""
        return {"executive_summary": content, "raw": content}
    except Exception:
        return {}

def generate_llm_derived_suggestions(bundle: dict[str, Any], model: str | None = None):
    client = _client()
    if client is None:
        return {}
    model = model or os.getenv("LMSTUDIO_MODEL", "")
    if not model:
        return {}
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Eres un arquitecto de datos. Sugieres columnas derivadas útiles solo a partir del análisis determinista. Devuelve JSON válido con una lista 'suggestions'."},
                {"role": "user", "content": json.dumps(safe_json(bundle), ensure_ascii=False, indent=2)},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}
