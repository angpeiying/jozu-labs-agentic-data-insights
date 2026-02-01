from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd


def _is_id_like(series: pd.Series, *, n_rows: int) -> bool:
    """Heuristic: skip charts for identifier-like columns."""
    try:
        n_unique = int(series.nunique(dropna=True))
        if n_rows <= 0:
            return False
        unique_ratio = n_unique / float(n_rows)
        return unique_ratio >= 0.90
    except Exception:
        return False


def run_categorical_pack(df: pd.DataFrame, categorical_cols: List[str]) -> Dict[str, Any]:
    n_rows = int(df.shape[0])
    results: Dict[str, Any] = {}
    insights: List[Dict[str, Any]] = []
    charts: List[Dict[str, Any]] = []

    if not categorical_cols:
        return {
            "summary": {"n_cols": 0},
            "categoricals": {},
            "insights": [{"severity": "info", "title": "No categorical columns", "evidence": "", "recommendation": ""}],
            "charts": [],
            "vega_lite": None,
            "skipped": "No categorical columns.",
        }

    # Build stats for up to 8 categorical columns
    used_cols: List[str] = []
    for c in categorical_cols[:8]:
        if c not in df.columns:
            continue

        s = df[c]
        n_unique = int(s.nunique(dropna=True))
        vc = s.value_counts(dropna=True).head(10)

        results[c] = {
            "top_values": vc.to_dict(),
            "n_unique": n_unique,
        }
        used_cols.append(c)

        # insight: ID-like detection
        if _is_id_like(s, n_rows=n_rows):
            insights.append({
                "severity": "info",
                "title": f"Column '{c}' looks like an identifier",
                "evidence": f"Unique ratio ≈ {n_unique}/{n_rows}",
                "recommendation": "Exclude from categorical distribution charts and most modeling features.",
            })

    # Build charts: up to 2 non-ID-like columns, top10 + percent
    chart_cols = []
    for c in used_cols:
        if not _is_id_like(df[c], n_rows=n_rows):
            chart_cols.append(c)
        if len(chart_cols) >= 2:
            break

    for idx, c0 in enumerate(chart_cols):
        vc0 = df[c0].value_counts(dropna=True).head(10)
        total = int(vc0.sum()) if len(vc0) else 0
        chart_values = [
            {"value": str(k), "count": int(v), "pct": (float(v) / total * 100.0) if total else 0.0}
            for k, v in vc0.items()
        ]

        spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": f"Top values for {c0}",
            "data": {"values": chart_values},
            "mark": {"type": "bar", "color": "#4f46e5"},
            "encoding": {
                "x": {"field": "value", "type": "nominal", "sort": "-y", "title": c0},
                "y": {"field": "count", "type": "quantitative", "title": "Count"},
                "tooltip": [
                    {"field": "value", "type": "nominal"},
                    {"field": "count", "type": "quantitative"},
                    {"field": "pct", "type": "quantitative", "format": ".2f", "title": "Percent (%)"},
                ],
            },
        }

        charts.append({
            "id": f"cat_top_{idx+1}",
            "title": f"Top categories: {c0}",
            "spec": spec,
            "priority": 70 - idx * 5,
            "tags": ["categorical", "distribution"],
        })

    # Backward-compat: keep a single vega_lite
    vega_lite = charts[0]["spec"] if charts else None

    summary = {
        "n_cols": len(used_cols),
        "cols_used": used_cols,
    }

    if not charts:
        insights.append({
            "severity": "info",
            "title": "No categorical charts rendered",
            "evidence": "All candidate columns look like identifiers or have no values.",
            "recommendation": "Check categorical role detection or allow 'top N + Other' for high-cardinality columns.",
        })

    return {
        "summary": summary,
        "categoricals": results,
        "insights": insights,
        "charts": charts,
        "vega_lite": vega_lite,
    }
