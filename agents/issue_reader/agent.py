# agents/issue_reader/agent.py
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from state import AgentState, Issue
from agents.issue_reader.tools import (
    fetch_raw_issues, fetch_rule_details, fetch_source_snippet
)


class IssueReaderState(TypedDict):
    project_key: str
    branch: str
    raw_issues: List[Dict]
    rule_cache: Dict[str, Dict]
    issues: List[Issue]


def fetch_issues_node(state: IssueReaderState) -> dict:
    raw = fetch_raw_issues(state["project_key"], state["branch"])
    return {"raw_issues": raw}


def fetch_rule_details_node(state: IssueReaderState) -> dict:
    unique_rules = {i["rule"] for i in state["raw_issues"]}
    cache = {}
    for rule_key in unique_rules:
        cache[rule_key] = fetch_rule_details(rule_key)
    return {"rule_cache": cache}


def fetch_source_node(state: IssueReaderState) -> dict:
    issues: List[Issue] = []
    for raw in state["raw_issues"]:
        rule = state["rule_cache"].get(raw["rule"], {})
        line = raw.get("textRange", {}).get("startLine", 1)
        snippet = fetch_source_snippet(raw["component"], line)
        issues.append(Issue(
            issue_key=raw["key"],
            rule_id=raw["rule"],
            rule_description=rule.get("name", ""),
            remediation_guidance=rule.get("remFnBaseEffort", ""),
            severity=raw.get("severity", ""),
            file_path=raw["component"].split(":")[-1],
            line_start=line,
            line_end=raw.get("textRange", {}).get("endLine", line),
            code_snippet=snippet,
        ))
    return {"issues": issues}


def _build_graph():
    builder = StateGraph(IssueReaderState)
    builder.add_node("fetch_issues", fetch_issues_node)
    builder.add_node("fetch_rules", fetch_rule_details_node)
    builder.add_node("fetch_source", fetch_source_node)
    builder.add_edge(START, "fetch_issues")
    builder.add_edge("fetch_issues", "fetch_rules")
    builder.add_edge("fetch_rules", "fetch_source")
    builder.add_edge("fetch_source", END)
    return builder.compile()


_graph = _build_graph()


def issue_reader_node(state: AgentState) -> dict:
    result = _graph.invoke({
        "project_key": state["project_key"],
        "branch": state["branch"],
        "raw_issues": [],
        "rule_cache": {},
        "issues": [],
    })
    return {"issues": result["issues"], "issues_fetched": True}
