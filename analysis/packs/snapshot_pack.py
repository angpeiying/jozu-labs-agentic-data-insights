from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd


def run_snapshot_pack(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Snapshot / data quality pack.
    Produces charts ONLY when meaningful.
    Returns:
      {
        "shape": {...},
        "missing_by_col_top20": {...},
        "duplicate_rows": ...,
        "sample_rows": [...],
        "charts": [...],          # ✅ NEW (preferred)
        "skipped": "...",         # optional
      }
    """
    out: Dict[str, Any] = {}

    # Basic stats (always)
    out["shape"] = {"rows": int(df.shape[0]), "cols": int(df.shape[1])}
    out["duplicate_rows"] = int(df.duplicated().sum())
    out["sample_rows"] = df.head(5).to_dict(orient="records")

    # Missing values
    missing = df.isna().sum().sort_values(ascending=False).head(20)
    out["missing_by_col_top20"] = missing.to_dict()

    missing_df = (
        missing.reset_index()
        .rename(columns={"index": "column", 0: "missing"})
    )
    if "missing" not in missing_df.columns:
        missing_df.columns = ["column", "missing"]

    total_rows = max(int(df.shape[0]), 1)
    missing_df["percent"] = (missing_df["missing"] / total_rows) * 100.0

    # ✅ If no missing at all -> don't emit empty charts
    if float(missing_df["missing"].sum()) <= 0:
        out["charts"] = []
        out["skipped"] = "No missing values."
        return out

    # Otherwise: build charts
    values = missing_df.to_dict(orient="records")

    chart_missing_count = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Top missing values by column (count)",
        "data": {"values": values},
        "mark": {"type": "bar"},
        "encoding": {
            "y": {"field": "column", "type": "nominal", "sort": "-x", "title": "Column"},
            "x": {"field": "missing", "type": "quantitative", "title": "Missing count"},
            "tooltip": [
                {"field": "column", "type": "nominal"},
                {"field": "missing", "type": "quantitative"},
                {"field": "percent", "type": "quantitative", "format": ".2f", "title": "Missing %"},
            ],
        },
    }

    chart_missing_percent = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Top missing values by column (percent)",
        "data": {"values": values},
        "mark": {"type": "bar"},
        "encoding": {
            "y": {"field": "column", "type": "nominal", "sort": "-x", "title": "Column"},
            "x": {"field": "percent", "type": "quantitative", "title": "Missing %"},
            "tooltip": [
                {"field": "column", "type": "nominal"},
                {"field": "missing", "type": "quantitative", "title": "Missing count"},
                {"field": "percent", "type": "quantitative", "format": ".2f", "title": "Missing %"},
            ],
        },
    }

    out["charts"] = [
        {"id": "missing_count", "title": "Missing values (Top 20) — Count", "spec": chart_missing_count, "priority": 95, "tags": ["quality", "snapshot"]},
        {"id": "missing_percent", "title": "Missing values (Top 20) — Percent", "spec": chart_missing_percent, "priority": 95, "tags": ["quality", "snapshot"]},
    ]

    # Keep legacy field for backward compatibility (optional)
    out["vega_lite"] = chart_missing_count

    return out