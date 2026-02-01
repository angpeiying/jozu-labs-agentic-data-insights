from __future__ import annotations
import json
from typing import Dict, Any
from pydantic import ValidationError
from langchain_core.messages import SystemMessage, HumanMessage

from schemas.plan_schema import AnalysisPlan
from llm.prompts import PLANNER_SYSTEM

def plan_packs(llm, schema: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    payload = {"schema": schema, "profile": profile}
    resp = llm.invoke([SystemMessage(content=PLANNER_SYSTEM), HumanMessage(content=json.dumps(payload))])

    try:
        data = json.loads(resp.content)
        plan = AnalysisPlan(**data)
        return plan.model_dump()
    except (json.JSONDecodeError, ValidationError):
        roles = profile.get("roles", {})
        steps = [{"pack": "snapshot", "why": "Baseline dataset overview."}]
        if roles.get("categorical"):
            steps.append({"pack": "categorical", "why": "Categorical distribution overview."})
        if roles.get("datetime"):
            steps.append({"pack": "timeseries", "why": "Datetime + numeric indicates time trend analysis."})
        return {"dataset_type": "timeseries" if roles.get("datetime") else "tabular", "steps": steps[:3], "notes": "Fallback plan."}
