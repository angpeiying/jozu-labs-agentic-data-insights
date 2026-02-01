from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

PackName = Literal["snapshot", "categorical", "timeseries", "numeric"]

class PlanStep(BaseModel):
    pack: PackName
    why: str = Field(..., description="Why this pack is relevant to the dataset.")
    params: Dict[str, Any] = Field(default_factory=dict)  

class AnalysisPlan(BaseModel):
    dataset_type: Literal["tabular", "timeseries", "unknown"]
    steps: List[PlanStep]
    notes: Optional[str] = None  
