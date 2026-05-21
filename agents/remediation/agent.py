# agents/remediation/agent.py
from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, START, END
from state import AgentState, Issue, Fix, ValidationResult
import agents.remediation.tools as tools
from agents.remediation.patch import apply_patch, create_unified_diff


class RemediationState(TypedDict):
    issues_to_fix: List[Issue]
    rag_contexts: Dict[str, str]   # issue_key -> rag context string
    fixes: List[Fix]


def rag_retrieve_node(state: RemediationState) -> dict:
    rag_contexts: Dict[str, str] = {}
    for issue in state["issues_to_fix"]:
        docs = tools.rag_retrieve(issue["rule_id"], issue["code_snippet"])
        rag_contexts[issue["issue_key"]] = "\n---\n".join(
            f"{d['rule_key']}: {d['description']} Remediation: {d['remediation']}"
            for d in docs
        )
    return {"rag_contexts": rag_contexts}


def llm_fix_node(state: RemediationState) -> dict:
    fixes: List[Fix] = []
    for issue in state["issues_to_fix"]:
        fixed_snippet = tools.call_llm(
            rule_id=issue["rule_id"],
            rule_description=issue["rule_description"],
            remediation_guidance=issue["remediation_guidance"],
            rag_context=state["rag_contexts"].get(issue["issue_key"], ""),
            file_path=issue["file_path"],
            line_start=issue["line_start"],
            line_end=issue["line_end"],
            code_snippet=issue["code_snippet"],
        )
        file_content = tools.read_file(issue["file_path"])
        new_content = apply_patch(
            file_content,
            line_start=issue["line_start"],
            line_end=issue["line_end"],
            fixed_block=fixed_snippet,
        )
        diff = create_unified_diff(
            file_content, new_content, issue["file_path"],
            issue["line_start"], issue["line_end"]
        )
        tools.write_file(issue["file_path"], new_content)
        fixes.append(Fix(
            issue_key=issue["issue_key"],
            file_path=issue["file_path"],
            unified_diff=diff,
            original_snippet=issue["code_snippet"],
            fixed_snippet=fixed_snippet,
        ))
    return {"fixes": fixes}


def _build_graph():
    builder = StateGraph(RemediationState)
    builder.add_node("rag_retrieve", rag_retrieve_node)
    builder.add_node("llm_fix", llm_fix_node)
    builder.add_edge(START, "rag_retrieve")
    builder.add_edge("rag_retrieve", "llm_fix")
    builder.add_edge("llm_fix", END)
    return builder.compile()


_graph = _build_graph()


def remediation_node(state: AgentState) -> dict:
    vr: Optional[ValidationResult] = state.get("validation_result")
    issues_to_fix = vr["remaining_issues"] if vr else state["issues"]
    result = _graph.invoke({"issues_to_fix": issues_to_fix, "rag_contexts": {}, "fixes": []})
    return {
        "fixes": result["fixes"],
        "validation_result": None,   # reset so validator runs fresh
        "round_number": state["round_number"] + 1,
    }
