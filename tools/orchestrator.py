from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from typing import List, Tuple

import time
from typing import Callable, Optional


from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage

from schemas.types import AppState
from tools.config import put_df, get_df

from analysis.ingest import load_file, infer_schema
from analysis.profiler import basic_profile, infer_dataset_type

from analysis.packs.snapshot_pack import run_snapshot_pack
from analysis.packs.categorical_pack import run_categorical_pack
from analysis.packs.timeseries_pack import run_timeseries_pack
from analysis.packs.numeric_pack import run_numeric_pack

from analysis.hypothesis_verify import verify_hypotheses

from llm.client import get_llm
from llm.planner import plan_packs
from llm.narrator import write_report
from llm.prompts import HYPOTHESIS_SYSTEM

from ydata_profiling import ProfileReport

MAX_CHARTS_TOTAL = 12
MAX_CHARTS_PER_PACK = 3

def _normalize_pack_charts(pack_name: str, out: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Standardize charts output.
    Preferred: out["charts"] = [{id,title,spec,priority,tags}]
    Backward-compat: out["vega_lite"] -> one chart.
    """
    charts: List[Dict[str, Any]] = []

    if isinstance(out, dict) and isinstance(out.get("charts"), list):
        for ch in out["charts"]:
            if not isinstance(ch, dict):
                continue
            spec = ch.get("spec")
            if not isinstance(spec, dict):
                continue
            charts.append({
                "id": ch.get("id") or f"{pack_name}_chart_{len(charts)+1}",
                "title": ch.get("title") or pack_name,
                "spec": spec,
                "priority": int(ch.get("priority", 50)),
                "tags": ch.get("tags") or [pack_name],
                "pack": pack_name,
            })

    # legacy support
    elif isinstance(out, dict) and isinstance(out.get("vega_lite"), dict):
        charts.append({
            "id": f"{pack_name}_vega",
            "title": pack_name,
            "spec": out["vega_lite"],
            "priority": 50,
            "tags": [pack_name],
            "pack": pack_name,
        })

    return charts

def flatten_charts(pack_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for pack_name, pack in (pack_results or {}).items():
        for ch in (pack.get("charts") or []):
            items.append({
                "pack": pack_name,
                "title": ch.get("title") or pack_name,
                "spec": ch.get("spec"),
                "priority": int(ch.get("priority", 50)),
                "tags": ch.get("tags") or [pack_name],
                "id": ch.get("id") or f"{pack_name}_{len(items)}",
            })
    items.sort(key=lambda x: x.get("priority", 0), reverse=True)
    return items

def execute_packs(
    *,
    df,
    roles: Dict[str, Any],
    steps: List[Dict[str, Any]],
    emit_substep=None,   # function(pack, status, detail)
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    """
    Runs packs deterministically according to plan steps.
    Returns: (pack_results, packs, flattened_charts, errors)
    """
    results: Dict[str, Any] = {}
    packs: List[Dict[str, Any]] = []
    all_charts: List[Dict[str, Any]] = []
    errors: List[str] = []

    def emit(pack: str, status: str, detail: str):
        if emit_substep:
            emit_substep(pack, status, detail)

    for s in steps:
        pack = (s or {}).get("pack")
        if not pack:
            continue

        emit(pack, "running", "Running")

        try:
            if pack == "snapshot":
                out = run_snapshot_pack(df)

            elif pack == "categorical":
                cat_cols = roles.get("categorical", [])
                out = run_categorical_pack(df, cat_cols) if cat_cols else {"skipped": "No categorical columns."}

            elif pack == "timeseries":
                dt_cols = roles.get("datetime", [])
                num_cols = roles.get("numeric", [])
                out = run_timeseries_pack(df, dt_cols[0], num_cols) if (dt_cols and num_cols) else {"skipped": "No datetime+numeric."}

            elif pack == "numeric":
                num_cols = roles.get("numeric", [])
                id_like = roles.get("id_like", [])
                out = run_numeric_pack(df, num_cols, id_like) if num_cols else {"skipped": "No numeric columns."}
                results["numeric"] = out
                packs.append({"name": "numeric", **out})

            else:
                out = {"skipped": f"Unknown pack: {pack}"}

            results[pack] = out
            packs.append({"name": pack, **(out if isinstance(out, dict) else {"value": out})})

            pack_charts = _normalize_pack_charts(pack, out if isinstance(out, dict) else {})
            # cap per pack
            pack_charts = sorted(pack_charts, key=lambda x: x.get("priority", 50), reverse=True)[:MAX_CHARTS_PER_PACK]
            all_charts.extend(pack_charts)

            if isinstance(out, dict) and out.get("skipped"):
                emit(pack, "skipped", out["skipped"])
            else:
                emit(pack, "done", "OK")

        except Exception as e:
            errors.append(f"pack_error[{pack}]: {e}")
            results[pack] = {"skipped": f"Error: {e}"}
            emit(pack, "skipped", f"Error: {e}")

    # global cap
    all_charts = sorted(all_charts, key=lambda x: x.get("priority", 50), reverse=True)[:MAX_CHARTS_TOTAL]

    return results, packs, all_charts, errors

REPORT_DIR = Path("data/reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def _emit(cb: Optional[Callable[[dict], None]], **evt):
    if cb:
        evt.setdefault("ts", time.time())
        cb(evt)

def node_ingest(state: AppState) -> AppState:
    errors = state.get("errors", [])
    try:
        df = load_file(state["file_path"])
        df_id = put_df(df)
        schema = infer_schema(df)
        return {**state, "df_id": df_id, "schema": schema, "errors": errors}
    except Exception as e:
        errors.append(f"ingest_error: {e}")
        return {**state, "errors": errors}

def node_profile(state: AppState) -> AppState:
    errors = state.get("errors", [])
    if "df_id" not in state:
        errors.append("profile_error: missing df_id")
        return {**state, "errors": errors}

    df = get_df(state["df_id"])
    prof = basic_profile(df)
    dtype = infer_dataset_type(prof)
    return {**state, "profile": prof, "dataset_type": dtype, "errors": errors}


def node_ydata_profiling(state: AppState) -> AppState:
    """
    Generate ydata-profiling HTML report and save to data/reports/
    """
    errors = state.get("errors", [])
    try:
        df = get_df(state["df_id"])

        # If extremely large, you can sample here later.
        # df_for_profile = df.sample(min(len(df), 20000), random_state=42) if len(df) > 20000 else df
        df_for_profile = df

        report = ProfileReport(
            df_for_profile,
            title=f"Profiling Report - {state.get('file_name','dataset')}",
            explorative=True,
            minimal=False,
        )

        safe_name = (state.get("file_name") or "dataset").replace(" ", "_").replace("/", "_")
        out_path = REPORT_DIR / f"{safe_name}.profile.html"
        report.to_file(str(out_path))

        # served by FastAPI at /reports/<file>
        report_url = f"/reports/{out_path.name}"

        return {**state, "profiling_report_path": str(out_path), "profiling_report_url": report_url, "errors": errors}
    except Exception as e:
        errors.append(f"profiling_error: {e}")
        return {**state, "errors": errors}


def node_plan(state: AppState) -> AppState:
    llm = get_llm()
    plan = plan_packs(llm, state.get("schema", {}), state.get("profile", {}))

    # deterministic add-on (safe)
    roles = (state.get("profile") or {}).get("roles", {})
    if roles.get("numeric"):
        steps = plan.get("steps", [])
        if not any(s.get("pack") == "numeric" for s in steps):
            steps.append({"pack": "numeric", "why": "Numeric columns detected; show distributions and correlations."})
        plan["steps"] = steps

    return {**state, "plan": plan}


def node_run_packs(state: AppState) -> AppState:
    errors = state.get("errors", [])
    df = get_df(state["df_id"])

    profile = state.get("profile", {})
    roles = profile.get("roles", {})
    plan = state.get("plan", {})
    steps = plan.get("steps", [])

    results, packs, charts, pack_errors = execute_packs(df=df, roles=roles, steps=steps)
    errors.extend(pack_errors)

    return {
        **state,
        "pack_results": results,
        "packs": packs,
        "deterministic_packs": packs,
        "charts": charts,
        "errors": errors,
    }

def node_hypotheses(state: AppState) -> AppState:
    llm = get_llm()
    payload = {"schema": state.get("schema", {}), "profile": state.get("profile", {}), "pack_results": state.get("pack_results", {})}
    resp = llm.invoke([SystemMessage(content=HYPOTHESIS_SYSTEM), HumanMessage(content=json.dumps(payload))])

    try:
        hypotheses = json.loads(resp.content)
        if not isinstance(hypotheses, list):
            hypotheses = []
    except Exception:
        hypotheses = []

    return {**state, "hypotheses": hypotheses}


def node_verify(state: AppState) -> AppState:
    df = get_df(state["df_id"])
    verified = verify_hypotheses(df, state.get("hypotheses", []), state.get("profile", {}))
    return {**state, "verified_hypotheses": verified}


def node_narrate(state: AppState) -> AppState:
    llm = get_llm()
    summary = {
        "file_name": state.get("file_name"),
        "schema": state.get("schema", {}),
        "profile": state.get("profile", {}),
        "profiling_report_url": state.get("profiling_report_url"),
        "plan": state.get("plan", {}),
        "pack_results": state.get("pack_results", {}),
        "verified_hypotheses": state.get("verified_hypotheses", []),
        "errors": state.get("errors", []),
    }
    report = write_report(llm, summary)
    
    structured = report
    if isinstance(report, dict) and "text" in report and isinstance(report["text"], str):
        try:
            structured = json.loads(report["text"])
        except Exception:
            structured = {"summary": {"dataset_overview": report["text"]}, "insights": [], "data_quality_notes": [], "next_steps": []}

    # Attach deterministic artifacts for UI rendering
    structured["pack_results"] = state.get("pack_results", {})
    structured["profiling_report_url"] = state.get("profiling_report_url")

    # ALWAYS attach charts (even if empty) so UI can render proper empty-state
    structured["charts"] = flatten_charts(state.get("pack_results", {})) or []

    return {**state, "report": structured}


def build_graph():
    g = StateGraph(AppState)

    g.add_node("ingest", node_ingest)
    g.add_node("profile", node_profile)
    g.add_node("ydata_profile", node_ydata_profiling)
    g.add_node("plan", node_plan)
    g.add_node("run_packs", node_run_packs)
    g.add_node("hypotheses", node_hypotheses)
    g.add_node("verify", node_verify)
    g.add_node("narrate", node_narrate)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "profile")
    g.add_edge("profile", "ydata_profile")
    g.add_edge("ydata_profile", "plan")
    g.add_edge("plan", "run_packs")
    g.add_edge("run_packs", "hypotheses")
    g.add_edge("hypotheses", "verify")
    g.add_edge("verify", "narrate")
    g.add_edge("narrate", END)

    return g.compile()

GRAPH = build_graph()

# def run_pipeline(file_path: str, file_name: str) -> Dict[str, Any]:
#     init_state: AppState = {"file_path": file_path, "file_name": file_name, "errors": []}
#     final = GRAPH.invoke(init_state)
#     return final.get("report", {"text": "No report generated."})

def run_pipeline_with_progress(file_path: str, file_name: str, progress_cb=None) -> Dict[str, Any]:
    step_index = {
        "ingest": 0,
        "profile": 1,
        "ydata_profile": 2,
        "plan": 3,
        "run_packs": 4,
        "hypotheses": 5,
        "verify": 6,
        "narrate": 7,
    }
    total_steps = len(step_index)
    step_start_ts: Dict[str, float] = {}

    def progress_for(step: str, status: str) -> int:
        i = step_index.get(step, 0)
        if status == "done":
            return int(((i + 1) / total_steps) * 100)
        return int((i / total_steps) * 100)

    def wrap(node_fn, step_name: str, start_msg: str, done_msg: str):
        def _wrapped(state: AppState) -> AppState:
            step_start_ts[step_name] = time.time()
            _emit(progress_cb,
                  type="step",
                  step=step_name,
                  status="running",
                  detail=start_msg,
                  progress_pct=progress_for(step_name, "running"))
            out = node_fn(state)
            dur = int((time.time() - step_start_ts[step_name]) * 1000)
            _emit(progress_cb,
                  type="step",
                  step=step_name,
                  status="done",
                  detail=done_msg,
                  duration_ms=dur,
                  progress_pct=progress_for(step_name, "done"))
            return out
        return _wrapped

    def run_packs_with_substeps(state: AppState) -> AppState:
        out_state = dict(state)
        errors = out_state.get("errors", [])

        df = get_df(out_state["df_id"])
        profile = out_state.get("profile", {})
        roles = profile.get("roles", {})

        plan = out_state.get("plan", {})
        steps = plan.get("steps", [])

        def emit_sub(pack: str, status: str, detail: str):
            _emit(progress_cb, type="substep", step="run_packs", name=pack, status=status, detail=detail)

        results, packs, charts, pack_errors = execute_packs(df=df, roles=roles, steps=steps, emit_substep=emit_sub)
        errors.extend(pack_errors)

        out_state["pack_results"] = results
        out_state["packs"] = packs
        out_state["deterministic_packs"] = packs
        out_state["charts"] = charts
        out_state["errors"] = errors
        return out_state

    g = StateGraph(AppState)
    g.add_node("ingest", wrap(node_ingest, "ingest", "Loading file + schema", "Ingested"))
    g.add_node("profile", wrap(node_profile, "profile", "Profiling columns + roles", "Profiled"))
    g.add_node("ydata_profile", wrap(node_ydata_profiling, "ydata_profile", "Generating ydata-profiling HTML report", "Profiling report saved"))
    g.add_node("plan", wrap(node_plan, "plan", "LLM planning analysis packs", "Plan created"))
    g.add_node("run_packs", wrap(run_packs_with_substeps, "run_packs", "Running analysis packs", "Packs complete"))
    g.add_node("hypotheses", wrap(node_hypotheses, "hypotheses", "LLM generating testable hypotheses", "Hypotheses created"))
    g.add_node("verify", wrap(node_verify, "verify", "Verifying hypotheses with code", "Verification complete"))
    g.add_node("narrate", wrap(node_narrate, "narrate", "LLM writing final report", "Report generated"))

    g.set_entry_point("ingest")
    g.add_edge("ingest", "profile")
    g.add_edge("profile", "ydata_profile")
    g.add_edge("ydata_profile", "plan")
    g.add_edge("plan", "run_packs")
    g.add_edge("run_packs", "hypotheses")
    g.add_edge("hypotheses", "verify")
    g.add_edge("verify", "narrate")
    g.add_edge("narrate", END)

    graph = g.compile()

    _emit(progress_cb, type="meta", status="started", detail=f"Job started for {file_name}", progress_pct=0)
    init_state: AppState = {"file_path": file_path, "file_name": file_name, "errors": []}
    final = graph.invoke(init_state)
    _emit(progress_cb, type="meta", status="finished", detail="Job finished", progress_pct=100)

    return final.get("report", {"text": "No report generated."})