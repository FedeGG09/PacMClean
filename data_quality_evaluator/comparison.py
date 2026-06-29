from __future__ import annotations
from typing import Any

def compare_profiles(current: dict[str, Any], reference: dict[str, Any]):
    cur_cols = set(current["profiles"].keys())
    ref_cols = set(reference["profiles"].keys())
    missing_cols = sorted(list(ref_cols - cur_cols))
    extra_cols = sorted(list(cur_cols - ref_cols))
    type_changes = []
    for col in sorted(cur_cols & ref_cols):
        cur_t = current["inferred_schema"].get(col)
        ref_t = reference["inferred_schema"].get(col)
        if cur_t != ref_t:
            type_changes.append({"column": col, "current": cur_t, "reference": ref_t})
    return {
        "schema_drift": {
            "missing_columns": missing_cols,
            "extra_columns": extra_cols,
            "type_changes": type_changes,
        },
        "row_count_current": current["row_count"],
        "row_count_reference": reference["row_count"],
    }
