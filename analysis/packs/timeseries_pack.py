from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd


def run_timeseries_pack(df: pd.DataFrame, datetime_col: str, numeric_cols: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "datetime_col": datetime_col,
        "numeric_cols": numeric_cols[:5],
        "insights": [],
        "charts": [],
    }

    if datetime_col not in df.columns:
        out["skipped"] = f"Datetime column '{datetime_col}' not found."
        return out

    d = df.copy()
    d[datetime_col] = pd.to_datetime(d[datetime_col], errors="coerce")
    d = d.dropna(subset=[datetime_col]).sort_values(datetime_col)

    out["n_points"] = int(len(d))
    if len(d) == 0 or not numeric_cols:
        out["skipped"] = "Not enough datetime rows or no numeric columns."
        return out

    # Keep only numeric cols that exist
    use_num = [c for c in numeric_cols if c in d.columns]
    if not use_num:
        out["skipped"] = "No numeric columns found in dataframe."
        return out

    d = d.set_index(datetime_col)
    daily = d[use_num].resample("D").mean().dropna(how="all")

    out["daily_head"] = daily.head(10).to_dict()
    out["daily_tail"] = daily.tail(10).to_dict()

    col0 = use_num[0]
    if col0 in daily.columns and len(daily) >= 2:
        first = float(daily[col0].iloc[0])
        last = float(daily[col0].iloc[-1])
        out["trend_first_last"] = {"col": col0, "first": first, "last": last, "delta": last - first}

        # simple insight
        direction = "increased" if (last - first) > 0 else "decreased" if (last - first) < 0 else "stayed flat"
        out["insights"].append({
            "severity": "info",
            "title": f"'{col0}' {direction} over the observed period",
            "evidence": f"First={first:.4g}, Last={last:.4g}, Delta={(last-first):.4g}",
            "recommendation": "Consider checking seasonality or outliers using weekly/monthly aggregation.",
        })

    daily_reset = daily.reset_index()
    if daily_reset.columns[0] != datetime_col:
        daily_reset = daily_reset.rename(columns={daily_reset.columns[0]: datetime_col})

    # Chart 1: daily line for first numeric
    spec_line = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": f"Daily trend: {col0}",
        "data": {"values": daily_reset[[datetime_col, col0]].to_dict(orient="records")},
        "mark": {"type": "line", "point": True, "color": "#4f46e5"},
        "encoding": {
            "x": {"field": datetime_col, "type": "temporal", "title": "Date"},
            "y": {"field": col0, "type": "quantitative", "title": col0},
            "tooltip": [
                {"field": datetime_col, "type": "temporal"},
                {"field": col0, "type": "quantitative"},
            ],
        },
    }

    out["charts"].append({
        "id": "ts_daily_line",
        "title": f"Daily trend — {col0}",
        "spec": spec_line,
        "priority": 85,
        "tags": ["timeseries", "trend"],
    })

    # Chart 2: rolling mean (7D) if enough points
    if len(daily) >= 14:
        roll = daily[[col0]].rolling(7, min_periods=3).mean().reset_index()
        if roll.columns[0] != datetime_col:
            roll = roll.rename(columns={roll.columns[0]: datetime_col})

        spec_roll = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "description": f"7-day rolling average: {col0}",
            "data": {"values": roll.to_dict(orient="records")},
            "mark": {"type": "line", "point": False, "color": "#4f46e5"},
            "encoding": {
                "x": {"field": datetime_col, "type": "temporal", "title": "Date"},
                "y": {"field": col0, "type": "quantitative", "title": f"{col0} (7D avg)"},
                "tooltip": [
                    {"field": datetime_col, "type": "temporal"},
                    {"field": col0, "type": "quantitative"},
                ],
            },
        }

        out["charts"].append({
            "id": "ts_rolling_7d",
            "title": f"Rolling average (7D) — {col0}",
            "spec": spec_roll,
            "priority": 80,
            "tags": ["timeseries", "smoothing"],
        })

    # Backward-compat: keep one vega_lite
    out["vega_lite"] = spec_line
    return out
