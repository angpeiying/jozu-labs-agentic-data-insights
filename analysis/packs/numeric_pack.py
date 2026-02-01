from __future__ import annotations
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

def run_numeric_pack(df: pd.DataFrame, numeric_cols: List[str], id_like: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Numeric pack:
      - Correlation heatmap (excluding id_like)
      - Up to 2 histograms (excluding id_like)
    Returns:
      {
        "summary": {...},
        "charts": [...],
        "skipped": "..."
      }
    """
    out: Dict[str, Any] = {"summary": {}, "charts": []}

    id_like_set = set(id_like or [])

    if not numeric_cols:
        out["skipped"] = "No numeric columns."
        return out

    # ✅ remove id-like numeric columns
    cols = [
        c for c in numeric_cols
        if c in df.columns
        and pd.api.types.is_numeric_dtype(df[c])
        and c not in id_like_set
    ]

    if not cols:
        out["skipped"] = "No usable numeric columns (numeric columns look like IDs)."
        return out

    # Summary
    desc = df[cols].describe().T
    out["summary"]["numeric_cols"] = cols[:12]
    out["summary"]["basic_stats"] = desc[["mean", "std", "min", "max"]].head(8).round(4).to_dict(orient="index")

    # -----------------------
    # Correlation heatmap
    # -----------------------
    N_CORR = min(12, len(cols))
    top_cols = (
        df[cols].notna().sum()
        .sort_values(ascending=False)
        .head(N_CORR)
        .index
        .tolist()
    )

    d = df[top_cols].copy()
    if len(d) > 50000:
        d = d.sample(50000, random_state=42)

    corr = d.corr(numeric_only=True).fillna(0.0)

    corr_rows = []
    for r in corr.index:
        for c in corr.columns:
            corr_rows.append({"x": str(r), "y": str(c), "corr": float(corr.loc[r, c])})

    corr_spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Correlation heatmap (numeric columns)",
        "data": {"values": corr_rows},
        "mark": {"type": "rect"},
        "encoding": {
            "x": {"field": "x", "type": "nominal", "title": None},
            "y": {"field": "y", "type": "nominal", "title": None},
            "color": {
                "field": "corr",
                "type": "quantitative",
                "title": "corr",
                "scale": {"domain": [-1, 1]},
            },
            "tooltip": [
                {"field": "x", "type": "nominal"},
                {"field": "y", "type": "nominal"},
                {"field": "corr", "type": "quantitative", "format": ".2f"},
            ],
        },
    }

    out["charts"].append({
        "id": "numeric_corr",
        "title": "Correlation heatmap",
        "spec": corr_spec,
        "priority": 95,
        "tags": ["numeric"]
    })

    # -----------------------
    # Histograms (top variance)
    # -----------------------
    var_rank = df[cols].var(numeric_only=True).sort_values(ascending=False)
    hist_cols = [c for c in var_rank.index.tolist()][:2]

    for i, col in enumerate(hist_cols, start=1):
        s = df[col].dropna()
        if s.empty:
            continue
        if len(s) > 20000:
            s = s.sample(20000, random_state=42)

        values = [{"value": float(v)} for v in s.values.astype(float)]

        hist_spec = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": f"Histogram for {col}",
            "data": {"values": values},
            "mark": {"type": "bar"},
            "encoding": {
                "x": {"field": "value", "type": "quantitative", "bin": {"maxbins": 30}, "title": col},
                "y": {"aggregate": "count", "type": "quantitative", "title": "Count"},
                "tooltip": [
                    {"field": "value", "type": "quantitative", "bin": True, "title": col},
                    {"aggregate": "count", "type": "quantitative", "title": "Count"},
                ],
            },
        }

        out["charts"].append({
            "id": f"numeric_hist_{i}",
            "title": f"Histogram: {col}",
            "spec": hist_spec,
            "priority": 80,
            "tags": ["numeric"]
        })

    return out
