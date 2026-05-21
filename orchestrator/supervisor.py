# orchestrator/supervisor.py
from typing import Literal
from langgraph.graph import StateGraph, START, END
from state import AgentState
from agents.issue_reader.agent import issue_reader_node
from agents.remediation.agent import remediation_node
from agents.validation.agent import validation_node
from agents.github.agent import github_node

Route = Literal["issue_reader", "remediator", "validator", "github_agent", "__end__"]


def route(state: AgentState) -> Route:
    if not state["issues"]:
        if state.get("issues_fetched"):
            return END
        return "issue_reader"
    if not state["fixes"]:
        return "remediator"
    if state["validation_result"] is None:
        return "validator"
    vr = state["validation_result"]
    if vr["remaining_issues"] and state["round_number"] < state["max_rounds"]:
        return "remediator"
    return "github_agent"


def _noop(state: AgentState) -> dict:
    return {}


def build_supervisor(checkpointer=None):
    builder = StateGraph(AgentState)

    builder.add_node("router", _noop)
    builder.add_node("issue_reader", issue_reader_node)
    builder.add_node("remediator", remediation_node)
    builder.add_node("validator", validation_node)
    builder.add_node("github_agent", github_node)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router", route,
        {
            "issue_reader": "issue_reader",
            "remediator": "remediator",
            "validator": "validator",
            "github_agent": "github_agent",
            END: END,
        },
    )
    builder.add_edge("issue_reader", "router")
    builder.add_edge("remediator", "router")
    builder.add_edge("validator", "router")
    builder.add_edge("github_agent", END)

    return builder.compile(checkpointer=checkpointer)
