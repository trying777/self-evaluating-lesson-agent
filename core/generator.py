"""Lesson Generator Node with persona grounding, deliberate error injection, and retry synthesis."""

import os
from typing import Dict, Any
from core.state import AgentState

# Deliberate flawed lesson used to demonstrate the evaluator catching errors on camera
DELIBERATE_ERROR_DRAFT = """# Introduction to RAG

Retrieval-Augmented Generation is an algorithmic optimization paradigm for generative models.
By computing high-dimensional cosine similarity across dense vector embeddings in a latent Riemannian manifold,
the neural decoder minimizes cross-entropy perplexity over parametric parameters.

## Vector Mathematics
Given a query vector q and document vector d:
Similarity(q, d) = (q · d) / (||q|| ||d||)

This achieves state-of-the-art BLEU and ROUGE metrics without requiring full parameter backpropagation.
"""

PERSONA_SYSTEM_PROMPT = """You are an empathetic, world-class educator teaching in India.
Your student is an ambitious 12th-grade graduate from a regional-language / non-English-medium school.
They know simple conversational English, have ZERO background in Artificial Intelligence or programming, and want to kickstart an AI career.

TOPIC: {topic}

CORE PEDAGOGICAL REQUIREMENTS:
1. WHAT IT IS: Explain RAG simply as "giving an AI an open book to search before it answers."
2. WHY IT MATTERS: Explain the real problem first! Normal AI models (like ChatGPT) only know what they studied in the past (closed-book exam). They don't know your private notes, company data, or yesterday's news. They can also confidently make things up (called "hallucination").
3. HOW IT WORKS (3 Simple Steps):
   - Step 1: Search (Retrieval) - Find the exact paragraph or page needed.
   - Step 2: Attach (Augmentation) - Paste that paragraph into the question.
   - Step 3: Answer (Generation) - The AI reads the page and answers accurately.
4. RELATABLE ANALOGY: Use the "Open-Book Exam vs. Closed-Book Exam" or "Doctor checking a patient's medical file before giving medicine" analogy.

STRICT TONE & LANGUAGE CONSTRAINTS:
- Use simple, short English sentences (aim for under 15-18 words per sentence).
- NO unexplained technical buzzwords. If you must use a word like "Hallucination" or "Prompt", explain it immediately in brackets using simple words.
- Warm, motivating, and clear.

{sharpened_rules_section}
{critique_revision_section}
"""


def get_llm():
    """Initializes the Gemini model using LangChain."""
    from dotenv import load_dotenv
    load_dotenv()
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set. "
            "Please provide a free Google AI Studio API key."
        )
    model_name = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0.3,
        google_api_key=api_key,
    )


def generate_lesson_node(state: AgentState) -> Dict[str, Any]:
    """Generates the lesson draft based on persona constraints and feedback history."""
    revision = state.get("revision_count", 0)

    # 1. Deliberate error demonstration hook for Loom video
    if state.get("inject_deliberate_error", False) and revision == 0:
        return {
            "current_draft": DELIBERATE_ERROR_DRAFT.strip(),
            "inject_deliberate_error": False,  # Reset so subsequent retry generates properly
        }

    # 2. Format self-evolved guardrails from memory
    sharpened_rules = state.get("sharpened_rules", [])
    sharpened_section = ""
    if sharpened_rules:
        rules_text = "\n- ".join(sharpened_rules)
        sharpened_section = f"ACTIVE GUARDRAILS (From Past Failure Memory):\n- {rules_text}\n"

    # 3. Format critique from previous failed evaluation
    critique_section = ""
    rejection_log = state.get("rejection_log", [])
    if rejection_log:
        latest = rejection_log[-1]
        failed_checks_str = ", ".join(latest.get("failed_checkpoints", []))
        reasons_str = "\n".join([f"  * {r}" for r in latest.get("reasons", [])])
        guidance = latest.get("corrective_guidance", "")
        critique_section = (
            f"\nCRITICAL CORRECTIONS REQUIRED (Your previous draft was REJECTED):\n"
            f"Failed Checkpoints: {failed_checks_str}\n"
            f"Evaluator Rejection Reasons:\n{reasons_str}\n"
            f"Action Required: {guidance}\n"
            f"You MUST completely fix the above shortcomings in this new revision while keeping what worked."
        )

    prompt = PERSONA_SYSTEM_PROMPT.format(
        topic=state["topic"],
        sharpened_rules_section=sharpened_section,
        critique_revision_section=critique_section,
    )

    llm = get_llm()
    response = llm.invoke(prompt)
    
    # Cleanly extract string content across different SDK return formats
    raw_content = response.content
    if isinstance(raw_content, list):
        text_parts = []
        for part in raw_content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif isinstance(part, str):
                text_parts.append(part)
        draft_text = "\n".join(text_parts)
    else:
        draft_text = str(raw_content)

    return {"current_draft": draft_text}

