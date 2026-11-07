"""LangGraph State Machine definition for the Self-Evaluating Lesson Generator."""

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from core.state import AgentState
from core.generator import generate_lesson_node
from core.evaluator import evaluate_lesson_node
from core.feedback import synthesize_feedback_node
from memory.optimizer import derive_sharpened_rules
from memory.db import record_run, record_evaluation, init_db

# Hard bounded retry ceiling as requested in the assessment (max 1-2 retries)
MAX_REVISION_LIMIT = 2


def load_memory_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves self-evolved guardrails from persistent memory before generation."""
    init_db()
    sharpened_rules = derive_sharpened_rules()
    return {"sharpened_rules": sharpened_rules}


def evaluation_router(state: AgentState) -> Literal["ship_lesson", "regenerate", "max_retries_reached"]:
    """Conditional edge router: decides whether to ship, retry, or abort."""
    evaluation = state.get("evaluation")
    if not evaluation:
        return "regenerate"

    if evaluation.all_passed:
        return "ship_lesson"

    revision = state.get("revision_count", 0)
    if revision >= MAX_REVISION_LIMIT:
        return "max_retries_reached"

    return "regenerate"


def success_terminal_node(state: AgentState) -> Dict[str, Any]:
    """Finalizes and records a successful passing lesson."""
    evaluation = state["evaluation"]
    run_id = record_run(
        topic=state["topic"],
        target_persona=state["target_persona"],
        total_revisions=state.get("revision_count", 0),
        final_status="PASSED_SHIPPABLE",
    )
    record_evaluation(
        run_id=run_id,
        attempt_number=state.get("revision_count", 0),
        rubric_dict=evaluation.model_dump(),
        draft_text=state.get("current_draft", ""),
    )
    return {"final_status": "PASSED_SHIPPABLE"}


def fallback_terminal_node(state: AgentState) -> Dict[str, Any]:
    """Graceful termination when maximum retries are exhausted without a full pass."""
    evaluation = state.get("evaluation")
    run_id = record_run(
        topic=state["topic"],
        target_persona=state["target_persona"],
        total_revisions=state.get("revision_count", 0),
        final_status="FAILED_MAX_RETRIES_EXCEEDED",
    )
    if evaluation:
        record_evaluation(
            run_id=run_id,
            attempt_number=state.get("revision_count", 0),
            rubric_dict=evaluation.model_dump(),
            draft_text=state.get("current_draft", ""),
        )
    return {"final_status": "FAILED_MAX_RETRIES_EXCEEDED"}


def build_pipeline() -> StateGraph:
    """Builds and compiles the cyclic LangGraph workflow."""
    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("generator", generate_lesson_node)
    workflow.add_node("evaluator", evaluate_lesson_node)
    workflow.add_node("synthesize_feedback", synthesize_feedback_node)
    workflow.add_node("success_terminal", success_terminal_node)
    workflow.add_node("fallback_terminal", fallback_terminal_node)

    # 2. Define Flow & Transitions
    workflow.set_entry_point("load_memory")
    workflow.add_edge("load_memory", "generator")
    workflow.add_edge("generator", "evaluator")

    # 3. Conditional Branching
    workflow.add_conditional_edges(
        "evaluator",
        evaluation_router,
        {
            "ship_lesson": "success_terminal",
            "regenerate": "synthesize_feedback",
            "max_retries_reached": "fallback_terminal",
        },
    )

    # Loop back to generator on feedback
    workflow.add_edge("synthesize_feedback", "generator")

    # Terminate graph
    workflow.add_edge("success_terminal", END)
    workflow.add_edge("fallback_terminal", END)

    return workflow.compile()

