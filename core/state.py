"""State definitions and Pydantic schemas for the Self-Evaluating Lesson Generator."""

from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class CheckpointResult(BaseModel):
    """Evaluation result for an individual rubric checkpoint. No partial credit."""
    passed: bool = Field(
        description="Strict Boolean: True if this checkpoint is completely satisfied, False otherwise."
    )
    reason: str = Field(
        description="Concise diagnostic explanation detailing why it passed or failed, referencing evidence from the draft."
    )


class LessonRubric(BaseModel):
    """The strict binary evaluation rubric. All checks must pass for the lesson to ship."""
    check_accuracy: CheckpointResult = Field(
        description="Accurate & grounded: Factual correctness of RAG (Retrieval, Augmentation, Generation)."
    )
    check_persona_language: CheckpointResult = Field(
        description="Beginner-friendly language: Vocabulary accessible to an Indian 12th grader with non-English-medium background."
    )
    check_no_unexplained_jargon: CheckpointResult = Field(
        description="Clear, no unexplained jargon: Any AI/technical term is immediately grounded in plain words or an analogy."
    )
    check_teaches_by_analogy: CheckpointResult = Field(
        description="Teaches by example/analogy: Employs relatable real-world analogies (e.g. open-book vs closed-book exams)."
    )
    check_core_pillars: CheckpointResult = Field(
        description="Covers key points: Comprehensively explains What it is, Why it matters, and How it works."
    )
    check_coherent_flow: CheckpointResult = Field(
        description="Coherent teaching flow: Logical sequencing from intuition to mechanism to real-world application."
    )

    @property
    def all_passed(self) -> bool:
        """Returns True only if every single checkpoint passed without exception."""
        return all([
            self.check_accuracy.passed,
            self.check_persona_language.passed,
            self.check_no_unexplained_jargon.passed,
            self.check_teaches_by_analogy.passed,
            self.check_core_pillars.passed,
            self.check_coherent_flow.passed,
        ])

    def get_failures(self) -> List[Dict[str, str]]:
        """Collects all failing checkpoints and their reasons."""
        failures = []
        checks = [
            ("Accurate & Grounded", self.check_accuracy),
            ("Beginner-Friendly Language", self.check_persona_language),
            ("No Unexplained Jargon", self.check_no_unexplained_jargon),
            ("Teaches by Example/Analogy", self.check_teaches_by_analogy),
            ("Covers Key Points (What/Why/How)", self.check_core_pillars),
            ("Coherent Teaching Flow", self.check_coherent_flow),
        ]
        for name, check in checks:
            if not check.passed:
                failures.append({"checkpoint": name, "reason": check.reason})
        return failures


class RejectionLogEntry(BaseModel):
    """Structure for audit trail and rejection logs across retry cycles."""
    attempt_number: int
    failed_checkpoints: List[str]
    reasons: List[str]
    corrective_guidance: str


class AgentState(TypedDict):
    """Central state object passed between nodes in the LangGraph workflow."""
    topic: str
    target_persona: str
    revision_count: int
    current_draft: str
    evaluation: Optional[LessonRubric]
    rejection_log: List[Dict[str, Any]]
    sharpened_rules: List[str]
    inject_deliberate_error: bool
    final_status: str

