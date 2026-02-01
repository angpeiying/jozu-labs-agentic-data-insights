from __future__ import annotations
import uuid
from typing import Dict
import pandas as pd

_DF_STORE: Dict[str, pd.DataFrame] = {}

def put_df(df: pd.DataFrame) -> str:
    df_id = str(uuid.uuid4())
    _DF_STORE[df_id] = df
    return df_id

def get_df(df_id: str) -> pd.DataFrame:
    return _DF_STORE[df_id]
