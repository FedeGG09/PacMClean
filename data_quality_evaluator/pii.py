from __future__ import annotations
import re
import pandas as pd

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+", re.I)
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s-]?)?(\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{4}")
DNI_RE = re.compile(r"^\d{7,8}$")
CUIT_RE = re.compile(r"^\d{2}-?\d{8}-?\d{1}$")
CBU_RE = re.compile(r"^\d{22}$")

def _sample_hits(series):
    hits = []
    for v in series.dropna().astype(str).head(50):
        if EMAIL_RE.search(v):
            hits.append(("email", v))
        elif PHONE_RE.search(v):
            hits.append(("phone", v))
        elif DNI_RE.match(v.replace(".", "").replace(" ", "")):
            hits.append(("dni", v))
        elif CUIT_RE.match(v.replace(" ", "")):
            hits.append(("cuit", v))
        elif CBU_RE.match(v.replace(" ", "")):
            hits.append(("cbu", v))
    return hits

def detect_pii_findings(df: pd.DataFrame):
    findings = []
    for col in df.columns:
        s = df[col]
        hits = _sample_hits(s)
        if hits:
            findings.append({
                "id": f"pii_{col}",
                "type": "pii_detected",
                "severity": "high",
                "column": col,
                "count": len(hits),
                "examples": [v for _, v in hits[:5]],
                "message": f"Se detectaron posibles datos sensibles en '{col}'.",
                "suggested_action": {
                    "action_type": "mask_pii",
                    "parameters": {"column": col, "pii_types": list(sorted(set(t for t, _ in hits)))}
                }
            })
    return findings

def mask_pii_dataframe(df: pd.DataFrame, columns=None):
    columns = columns or df.columns.tolist()
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            continue
        s = out[col].astype(str)
        s = s.str.replace(EMAIL_RE, "[email]", regex=True)
        s = s.str.replace(PHONE_RE, "[phone]", regex=True)
        s = s.str.replace(CUIT_RE, "[cuit]", regex=True)
        s = s.str.replace(CBU_RE, "[cbu]", regex=True)
        out[col] = s
    return out
