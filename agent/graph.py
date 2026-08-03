"""LangGraph wiring for the Windows CLI agent.

Flow:
    generate -> validate -> (safety | retry | blocked)
    safety -> (execute | blocked)
    execute -> result_validation
    result_validation -> (END | retry)
    retry -> generate
    blocked -> END
"""

from __future__ import annotations

import uuid

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .nodes import (
    blocked_node,
    execute_node,
    generate_node,
    result_validation_node,
    retry_node,
    route_after_result_validation,
    route_after_safety,
    route_after_validation,
    safety_node,
    validate_node,
)
from .state import AgentState


def build_graph():
    """Build and compile the agent graph."""

    workflow = StateGraph(AgentState)

    workflow.add_node("generate", generate_node)
    workflow.add_node("validate", validate_node)
    workflow.add_node("safety", safety_node)
    workflow.add_node("execute", execute_node)
    workflow.add_node("result_validation", result_validation_node)
    workflow.add_node("retry", retry_node)
    workflow.add_node("blocked", blocked_node)

    workflow.set_entry_point("generate")

    workflow.add_edge("generate", "validate")

    workflow.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "safety": "safety",
            "retry": "retry",
            "blocked": "blocked",
        },
    )

    workflow.add_conditional_edges(
        "safety",
        route_after_safety,
        {
            "execute": "execute",
            "blocked": "blocked",
        },
    )

    workflow.add_edge("execute", "result_validation")

    workflow.add_conditional_edges(
        "result_validation",
        route_after_result_validation,
        {
            "end": END,
            "retry": "retry",
        },
    )

    workflow.add_edge("retry", "generate")
    workflow.add_edge("blocked", END)

    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["execute"],
    )


def new_thread_config() -> dict:
    """Create a fresh thread ID for one run."""

    return {
        "configurable": {
            "thread_id": str(uuid.uuid4())
        }
    }