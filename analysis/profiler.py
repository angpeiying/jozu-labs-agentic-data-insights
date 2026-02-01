from __future__ import annotations
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

def detect_datetime_columns(df: pd.DataFrame) -> List[str]:
    out: List[str] = []
    for c in df.columns:
        s = df[c]
        if np.issubdtype(s.dtype, np.datetime64):
            out.append(str(c))
            continue
        if s.dtype == object:
            sample = s.dropna().astype(str).head(50)
            if sample.empty:
                continue
            parsed = pd.to_datetime(sample, errors="coerce")
            if parsed.notna().mean() > 0.7:
                out.append(str(c))
    return out

def column_roles(df: pd.DataFrame) -> Dict[str, List[str]]:
    numeric = [str(c) for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    categorical = [str(c) for c in df.columns if (df[c].dtype == object) or pd.api.types.is_categorical_dtype(df[c])]
    datetime_cols = detect_datetime_columns(df)

    # remove datetime from categorical (if parsed as object)
    categorical = [c for c in categorical if c not in datetime_cols]

    id_like: List[str] = []
    n = len(df)
    for c in df.columns:
        if n <= 0:
            continue
        nunique = df[c].nunique(dropna=True)
        if nunique > 20 and (nunique / max(n, 1)) > 0.9:
            id_like.append(str(c))

    return {"numeric": numeric, "categorical": categorical, "datetime": datetime_cols, "id_like": id_like}

def basic_profile(df: pd.DataFrame) -> Dict[str, Any]:
    roles = column_roles(df)
    return {
        "roles": roles,
        "missing_total": int(df.isna().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "top_categoricals": {
            c: df[c].value_counts(dropna=True).head(5).to_dict()
            for c in roles["categorical"][:8]
        },
        "numeric_summary": df[roles["numeric"]].describe().to_dict() if roles["numeric"] else {},
    }

def infer_dataset_type(profile: Dict[str, Any]) -> str:
    roles = profile.get("roles", {})
    if roles.get("datetime") and roles.get("numeric"):
        return "timeseries"
    if roles.get("numeric") or roles.get("categorical"):
        return "tabular"
    return "unknown"
