from __future__ import annotations
import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from llm.prompts import NARRATOR_SYSTEM

def write_report(llm, summary: Dict[str, Any]) -> Dict[str, Any]:
    resp = llm.invoke([SystemMessage(content=NARRATOR_SYSTEM), HumanMessage(content=json.dumps(summary))])
    return {"text": resp.content}
