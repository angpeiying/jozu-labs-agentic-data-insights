from __future__ import annotations
from typing import Any, Dict, List, TypedDict, Literal, Optional

DatasetType = Literal["tabular", "timeseries", "unknown"]

class AppState(TypedDict, total=False):
    file_path: str
    file_name: str

    df_id: str

    schema: Dict[str, Any]
    profile: Dict[str, Any]
    dataset_type: DatasetType

    profiling_report_path: str
    profiling_report_url: str

    plan: Dict[str, Any]           # (you can store validated model_dump later)
    pack_results: Dict[str, Any]

    packs: List[Dict[str, Any]]
    deterministic_packs: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]

    hypotheses: List[Dict[str, Any]]
    verified_hypotheses: List[Dict[str, Any]]

    report: Dict[str, Any]
    errors: List[str]
