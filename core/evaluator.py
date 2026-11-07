"""Strict Binary Rubric Evaluator Node. Enforces hard pass/fail quality gates."""

import os
from typing import Dict, Any
from core.state import AgentState, LessonRubric

EVALUATOR_SYSTEM_PROMPT = """You are an unyielding, strict Content Systems Quality Auditor.
Your mandate: Determine if the drafted AI lesson is truly good enough to ship to a 12th-grade student from India with limited English vocabulary and a non-English-medium schooling background.

There is NO partial credit. Each of the following 6 checkpoints must be evaluated as a strict Boolean (True or False) with evidence:

1. check_accuracy:
   - PASS (True): RAG is accurately grounded. Clear distinction between Retrieval (searching stored documents), Augmentation (adding context to the prompt), and Generation (drafting the answer).
   - FAIL (False): Factual inaccuracies, confusing RAG with fine-tuning, or misleading technical claims.

2. check_persona_language:
   - PASS (True): Words and sentences are simple, clean, and accessible to a student whose first language is not English. Sentences are mostly short and readable.
   - FAIL (False): Dense academic prose, excessive prepositional phrases, or college-level English vocabulary.

3. check_no_unexplained_jargon:
   - PASS (True): Every technical AI term (e.g., 'hallucination', 'prompts', 'LLM', 'embeddings') is immediately grounded in plain language or an intuitive analogy.
   - FAIL (False): Technical buzzwords appear naked without immediate explanation, or mathematical formulas (cosine similarity, matrices, vectors) are dumped without intuition.

4. check_teaches_by_analogy:
   - PASS (True): Teaches the concept using a relatable everyday analogy (such as Open-Book vs Closed-Book exams, a chef looking up a recipe book, or a doctor checking patient records).
   - FAIL (False): Abstract explanations only; no relatable analogy provided.

5. check_core_pillars:
   - PASS (True): Distinctly and clearly covers: (1) What RAG is, (2) Why it matters / the exact problem it solves, and (3) How it works step-by-step.
   - FAIL (False): Skips or skimps on any one of the three pillars (e.g., forgets to explain why normal LLMs fail without it).

6. check_coherent_flow:
   - PASS (True): Logical pedagogical progression: starts with a problem the student can feel, introduces the concept as the hero, walks through how it works, and finishes with a clear summary.
   - FAIL (False): Disjointed sections, abrupt jumps, or confusing ordering.

Be objective and rigorous. Do not give the benefit of the doubt. If any checkpoint fails, provide a clear, constructive explanation in the 'reason' field so the generator knows exactly what to fix.
"""


def get_evaluator_llm():
    """Initializes the structured Gemini evaluator."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set."
        )
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.0,  # Zero temperature for deterministic evaluation
        google_api_key=api_key,
    )
    return llm.with_structured_output(LessonRubric)


def evaluate_lesson_node(state: AgentState) -> Dict[str, Any]:
    """Runs the lesson draft through the strict binary evaluation rubric."""
    draft = state.get("current_draft", "")
    prompt = f"{EVALUATOR_SYSTEM_PROMPT}\n\n---\nLESSON DRAFT TO EVALUATE:\n{draft}\n---"

    evaluator = get_evaluator_llm()
    rubric_result: LessonRubric = evaluator.invoke(prompt)

    return {"evaluation": rubric_result}
