"""Prompt and rubric optimization engine that sharpens instructions based on historical failures."""

from typing import List, Dict, Any
from pathlib import Path
from memory.db import get_failure_statistics, DEFAULT_DB_PATH


# Rule templates triggered by recurring failure modes
RULE_DISPATCH = {
    "No Unexplained Jargon": (
        "SELF-EVOLVED GUARDRAIL [Jargon Defense]: Historical audit logs reveal frequent jargon failures. "
        "Strict prohibition: If you write words like 'vector', 'embedding', 'tokens', or 'hallucination', "
        "you MUST immediately follow with a plain daily-life translation in parentheses or a direct analogy."
    ),
    "Beginner-Friendly Language": (
        "SELF-EVOLVED GUARDRAIL [Vocabulary Simplification]: Past evaluations flagged complex phrasing for the 12th-grade Indian persona. "
        "Write in simple, conversational English. Keep sentences under 16 words. Avoid academic or corporate vocabulary."
    ),
    "Teaches by Example/Analogy": (
        "SELF-EVOLVED GUARDRAIL [Mandatory Grounding]: Prior versions lacked concrete grounding. "
        "You MUST explicitly include the 'Open-Book vs. Closed-Book Exam' comparison when explaining why RAG is necessary."
    ),
    "Covers Key Points (What/Why/How)": (
        "SELF-EVOLVED GUARDRAIL [Structure Enforcement]: Previous iterations skipped or blended the core pillars. "
        "Explicitly separate sections: '1. Why LLMs Need Help (The Problem)', '2. What is RAG?', and '3. How RAG Works (Step-by-Step)'."
    ),
    "Coherent Teaching Flow": (
        "SELF-EVOLVED GUARDRAIL [Pedagogical Sequencing]: Ensure a linear bridge from student intuition to technical reality. "
        "Start with a pain point everyone knows before introducing any technology name."
    ),
    "Accurate & Grounded": (
        "SELF-EVOLVED GUARDRAIL [Technical Grounding]: Retain precise distinction between retrieval (search), augmentation (prompt injection), and generation (answer drafting)."
    ),
}


def derive_sharpened_rules(db_path: Path = DEFAULT_DB_PATH, failure_threshold: int = 1) -> List[str]:
    """
    Examines persistent memory and derives active guardrails based on failure frequency.
    Any checkpoint that has failed >= failure_threshold times gets its sharpened rule activated.
    """
    stats: Dict[str, int] = get_failure_statistics(db_path)
    sharpened_rules: List[str] = []

    # Sort checkpoints by failure frequency (highest first)
    sorted_failures = sorted(stats.items(), key=lambda item: item[1], reverse=True)

    for checkpoint_name, count in sorted_failures:
        if count >= failure_threshold and checkpoint_name in RULE_DISPATCH:
            sharpened_rules.append(RULE_DISPATCH[checkpoint_name])

    return sharpened_rules


def get_evolution_report(db_path: Path = DEFAULT_DB_PATH) -> Dict[str, Any]:
    """Returns an analytics overview of the agent's evolutionary state."""
    stats = get_failure_statistics(db_path)
    active_rules = derive_sharpened_rules(db_path)
    return {
        "failure_counts_by_checkpoint": stats,
        "active_sharpened_rules_count": len(active_rules),
        "active_sharpened_rules": active_rules,
    }
