# agents/validation/agent.py
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, START, END
from state import AgentState, Issue, ValidationResult
import agents.validation.tools as tools


class ValidationState(TypedDict):
    project_key: str
    branch: str
    issue_keys: List[str]
    original_issues: List[Issue]
    task_id: str
    validation_result: Optional[ValidationResult]


def trigger_scan_node(state: ValidationState) -> dict:
    task_id = tools.run_scan(state["project_key"])
    return {"task_id": task_id}


def poll_task_node(state: ValidationState) -> dict:
    tools.wait_for_scan(state["task_id"])
    return {}


def check_issues_node(state: ValidationState) -> dict:
    result = tools.check_resolved(
        state["project_key"],
        state["branch"],
        state["issue_keys"],
    )
    remaining_issues = _rebuild_issue_objects(
        result["remaining_raw"], state["original_issues"]
    )
    vr = ValidationResult(
        resolved_issues=result["resolved"],
        remaining_issues=remaining_issues,
        all_resolved=len(result["remaining_raw"]) == 0,
        round_number=0,
    )
    return {"validation_result": vr}


def _rebuild_issue_objects(remaining_raw: List[dict],
                            original_issues: List[Issue]) -> List[Issue]:
    original_by_key = {i["issue_key"]: i for i in original_issues}
    result = []
    for raw in remaining_raw:
        key = raw.get("issue_key") or raw.get("key", "")
        if key in original_by_key:
            result.append(original_by_key[key])
    return result


def _build_graph():
    builder = StateGraph(ValidationState)
    builder.add_node("trigger_scan", trigger_scan_node)
    builder.add_node("poll_task", poll_task_node)
    builder.add_node("check_issues", check_issues_node)
    builder.add_edge(START, "trigger_scan")
    builder.add_edge("trigger_scan", "poll_task")
    builder.add_edge("poll_task", "check_issues")
    builder.add_edge("check_issues", END)
    return builder.compile()


_graph = _build_graph()


def validation_node(state: AgentState) -> dict:
    issue_keys = [i["issue_key"] for i in state["issues"]]
    result = _graph.invoke({
        "project_key": state["project_key"],
        "branch": state["branch"],
        "issue_keys": issue_keys,
        "original_issues": state["issues"],
        "task_id": "",
        "validation_result": None,
    })
    vr = result["validation_result"]
    vr["round_number"] = state["round_number"]
    return {"validation_result": vr}
