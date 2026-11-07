"""Feedback synthesizer node. Extracts rejection diagnostics and prepares revision directives."""

from typing import Dict, Any, List
from core.state import AgentState, LessonRubric
from memory.db import record_rejection, record_evaluation


def synthesize_feedback_node(state: AgentState) -> Dict[str, Any]:
    """
    Diagnoses evaluation failures, logs rejection details into persistent memory,
    and constructs actionable guidance for the generator's next retry.
    """
    evaluation: LessonRubric = state["evaluation"]
    attempt_num = state.get("revision_count", 0)

    failed_items = evaluation.get_failures()
    failed_checkpoints: List[str] = [item["checkpoint"] for item in failed_items]
    reasons: List[str] = [item["reason"] for item in failed_items]

    # Synthesize concrete rewrite actions
    guidance_points = []
    for item in failed_items:
        name = item["checkpoint"]
        reason = item["reason"]
        if "Jargon" in name:
            guidance_points.append("Remove all mathematical formulas and naked buzzwords; explain any AI concept with a simple everyday metaphor.")
        elif "Language" in name:
            guidance_points.append("Shorten complex sentences; use simple vocabulary accessible to a 12th grader from a non-English-medium school.")
        elif "Analogy" in name:
            guidance_points.append("Integrate an explicit 'Open-Book vs. Closed-Book Exam' analogy to anchor the concept.")
        elif "Key Points" in name:
            guidance_points.append("Ensure distinct sections for (1) What it is, (2) Why it matters, and (3) How it works.")
        elif "Coherent Flow" in name:
            guidance_points.append("Restructure the lesson into a logical progression starting from the student's perspective.")
        elif "Grounded" in name:
            guidance_points.append("Verify factual correctness of retrieval, prompt augmentation, and response generation.")

    corrective_guidance = " | ".join(guidance_points)

    log_entry = {
        "attempt_number": attempt_num,
        "failed_checkpoints": failed_checkpoints,
        "reasons": reasons,
        "corrective_guidance": corrective_guidance,
    }

    current_log = list(state.get("rejection_log", []))
    current_log.append(log_entry)

    # Persist rejection to SQLite
    run_id = state.get("run_id", 1)
    try:
        record_evaluation(
            run_id=run_id,
            attempt_number=attempt_num,
            rubric_dict=evaluation.model_dump(),
            draft_text=state.get("current_draft", ""),
        )
        record_rejection(
            run_id=run_id,
            attempt_number=attempt_num,
            failed_checkpoints=failed_checkpoints,
            reasons=reasons,
            corrective_guidance=corrective_guidance,
        )
    except Exception as e:
        # Gracefully handle database logging in offline/test scenarios
        pass

    return {
        "rejection_log": current_log,
        "revision_count": attempt_num + 1,
    }

