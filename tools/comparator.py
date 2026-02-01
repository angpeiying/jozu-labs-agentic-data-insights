# tools/comparator.py
from __future__ import annotations
from typing import Any, Dict, List, Tuple


def _get_snapshot(report: Dict[str, Any]) -> Dict[str, Any]:
    pr = report.get("pack_results", {}) if isinstance(report.get("pack_results"), dict) else {}
    snap = pr.get("snapshot", {}) if isinstance(pr.get("snapshot"), dict) else {}
    return snap


def _top_missing(snap: Dict[str, Any], k: int = 10) -> List[Tuple[str, int]]:
    miss = snap.get("missing_by_col_top20", {})
    if not isinstance(miss, dict):
        return []
    items = [(str(col), int(v)) for col, v in miss.items()]
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:k]


def compare_reports(a: Dict[str, Any], b: Dict[str, Any], *, name_a: str, name_b: str) -> Dict[str, Any]:
    snap_a = _get_snapshot(a)
    snap_b = _get_snapshot(b)

    shape_a = snap_a.get("shape", {}) if isinstance(snap_a.get("shape"), dict) else {}
    shape_b = snap_b.get("shape", {}) if isinstance(snap_b.get("shape"), dict) else {}

    insights_a = a.get("insights", []) if isinstance(a.get("insights"), list) else []
    insights_b = b.get("insights", []) if isinstance(b.get("insights"), list) else []

    cmp_summary = {
        "dataset_a": name_a,
        "dataset_b": name_b,
        "metrics": {
            "rows": {"a": shape_a.get("rows"), "b": shape_b.get("rows"), "diff": (shape_b.get("rows", 0) or 0) - (shape_a.get("rows", 0) or 0)},
            "cols": {"a": shape_a.get("cols"), "b": shape_b.get("cols"), "diff": (shape_b.get("cols", 0) or 0) - (shape_a.get("cols", 0) or 0)},
            "duplicate_rows": {"a": snap_a.get("duplicate_rows"), "b": snap_b.get("duplicate_rows")},
            "insights_count": {"a": len(insights_a), "b": len(insights_b), "diff": len(insights_b) - len(insights_a)},
        },
        "top_missing_a": _top_missing(snap_a, 10),
        "top_missing_b": _top_missing(snap_b, 10),
    }

    # keep originals so UI can render both
    return {
        "mode": "compare",
        "comparison": cmp_summary,
        "report_a": a,
        "report_b": b,
        "profiling_report_url": None,  # you can expose both profiling urls inside comparison instead
        "errors": (a.get("errors", []) if isinstance(a.get("errors"), list) else []) + (b.get("errors", []) if isinstance(b.get("errors"), list) else []),
    }
