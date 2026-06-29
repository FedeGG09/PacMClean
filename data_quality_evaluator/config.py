from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import yaml

@dataclass
class AppConfig:
    null_high_threshold: float = 0.20
    null_medium_threshold: float = 0.05
    duplicate_high_threshold: float = 0.02
    outlier_iqr_multiplier: float = 1.5
    max_sample_values: int = 5
    min_date_parse_ratio: float = 0.60
    typo_distance_threshold: int = 2
    quality_weights: dict[str, float] = field(default_factory=lambda: {
        "missing": 25,
        "duplicates": 15,
        "outliers": 10,
        "invalid_dates": 15,
        "typos": 10,
        "pii": 10,
        "schema_drift": 10,
        "cross_checks": 15,
    })

def load_rules_file(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    return json.loads(text)
