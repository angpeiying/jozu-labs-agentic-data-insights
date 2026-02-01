# analysis/ingest.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import pandas as pd


def load_file(file_path: str) -> pd.DataFrame:
    p = Path(file_path)
    if not p.exists():
        raise FileNotFoundError(file_path)

    suffix = p.suffix.lower()

    # -------------------------
    # CSV
    # -------------------------
    if suffix == ".csv":
        try:
            df = pd.read_csv(p)
        except UnicodeDecodeError:
            df = pd.read_csv(p, encoding="latin1")

        return _postprocess_df(df)

    # -------------------------
    # Excel
    # -------------------------
    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(p)
        return _postprocess_df(df)

    # -------------------------
    # Parquet
    # -------------------------
    if suffix == ".parquet":
        # Requires: pip install pyarrow  (recommended)
        # or: pip install fastparquet
        df = pd.read_parquet(p)
        return _postprocess_df(df)

    # -------------------------
    # JSON Lines (JSONL / NDJSON)
    # -------------------------
    if suffix in (".jsonl", ".ndjson"):
        # Typical JSONL format: 1 JSON object per line
        try:
            df = pd.read_json(p, lines=True)
        except ValueError:
            # Fallback for "normal JSON" files that are arrays/dicts
            df = pd.read_json(p)

        return _postprocess_df(df)

    raise ValueError(f"Unsupported file type: {suffix}")


def _postprocess_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize common upload issues:
    - Ensure columns are strings
    - Drop pandas auto columns like 'Unnamed: 0'
    - Keep as simple as possible
    """
    # ensure string column names
    df.columns = [str(c) for c in df.columns]

    # drop auto-index columns from CSV exports
    unnamed = [c for c in df.columns if c.strip().lower().startswith("unnamed:")]
    if unnamed:
        df = df.drop(columns=unnamed, errors="ignore")

    return df


def infer_schema(df: pd.DataFrame) -> Dict[str, Any]:
    cols = []
    for c in df.columns:
        s = df[c]
        cols.append({
            "name": str(c),
            "dtype": str(s.dtype),
            "missing": int(s.isna().sum()),
            "n_unique": int(s.nunique(dropna=True)),
        })

    return {
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
        "columns": cols,
    }
