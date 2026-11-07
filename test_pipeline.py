"""Automated test suite verifying the rubric models, SQLite memory, and LangGraph workflow."""

import os
import unittest
from pathlib import Path
from core.state import LessonRubric, CheckpointResult, AgentState
from memory.db import init_db, record_run, record_evaluation, record_rejection, get_failure_statistics
from memory.optimizer import derive_sharpened_rules, get_evolution_report
from core.graph import evaluation_router, MAX_REVISION_LIMIT

TEST_DB_PATH = Path("test_memory.db")


class TestPipelineArchitecture(unittest.TestCase):

    def setUp(self):
        try:
            if TEST_DB_PATH.exists():
                TEST_DB_PATH.unlink()
        except PermissionError:
            pass
        init_db(TEST_DB_PATH)

    def tearDown(self):
        try:
            if TEST_DB_PATH.exists():
                TEST_DB_PATH.unlink()
        except PermissionError:
            pass

    def test_rubric_binary_contract_all_passed(self):
        rubric = LessonRubric(
            check_accuracy=CheckpointResult(passed=True, reason="Accurate"),
            check_persona_language=CheckpointResult(passed=True, reason="Simple English"),
            check_no_unexplained_jargon=CheckpointResult(passed=True, reason="No naked jargon"),
            check_teaches_by_analogy=CheckpointResult(passed=True, reason="Used exam analogy"),
            check_core_pillars=CheckpointResult(passed=True, reason="Covered What/Why/How"),
            check_coherent_flow=CheckpointResult(passed=True, reason="Logical flow"),
        )
        self.assertTrue(rubric.all_passed)
        self.assertEqual(len(rubric.get_failures()), 0)

    def test_rubric_binary_contract_single_failure(self):
        rubric = LessonRubric(
            check_accuracy=CheckpointResult(passed=True, reason="Accurate"),
            check_persona_language=CheckpointResult(passed=True, reason="Simple English"),
            check_no_unexplained_jargon=CheckpointResult(passed=False, reason="Unexplained 'cosine similarity' in para 2"),
            check_teaches_by_analogy=CheckpointResult(passed=True, reason="Used exam analogy"),
            check_core_pillars=CheckpointResult(passed=True, reason="Covered What/Why/How"),
            check_coherent_flow=CheckpointResult(passed=True, reason="Logical flow"),
        )
        self.assertFalse(rubric.all_passed)
        failures = rubric.get_failures()
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["checkpoint"], "No Unexplained Jargon")
        self.assertIn("cosine similarity", failures[0]["reason"])

    def test_sqlite_persistence_and_failure_statistics(self):
        run_id = record_run(
            topic="Introduction to RAG",
            target_persona="12th grade graduate India",
            total_revisions=1,
            final_status="PASSED_SHIPPABLE",
            db_path=TEST_DB_PATH,
        )
        self.assertIsInstance(run_id, int)

        # Record a rejection with jargon failure
        record_rejection(
            run_id=run_id,
            attempt_number=0,
            failed_checkpoints=["No Unexplained Jargon", "Beginner-Friendly Language"],
            reasons=["Heavy jargon", "Sentences too long"],
            corrective_guidance="Simplify vocabulary and remove math formulas",
            db_path=TEST_DB_PATH,
        )

        stats = get_failure_statistics(TEST_DB_PATH)
        self.assertEqual(stats["No Unexplained Jargon"], 1)
        self.assertEqual(stats["Beginner-Friendly Language"], 1)

    def test_self_evolving_guardrail_synthesis(self):
        # Simulate multiple historical failures in SQLite
        run_id = record_run("RAG", "12th grade", 2, "FAILED", db_path=TEST_DB_PATH)
        for _ in range(2):
            record_rejection(
                run_id=run_id,
                attempt_number=0,
                failed_checkpoints=["No Unexplained Jargon"],
                reasons=["Technical buzzwords dumped without analogies"],
                corrective_guidance="Add everyday analogies",
                db_path=TEST_DB_PATH,
            )

        # Ensure the optimizer automatically derives a sharpened rule from memory
        sharpened = derive_sharpened_rules(db_path=TEST_DB_PATH, failure_threshold=1)
        self.assertTrue(len(sharpened) >= 1)
        self.assertIn("Jargon Defense", sharpened[0])

    def test_routing_logic(self):
        # Case 1: All passed -> ship_lesson
        passing_rubric = LessonRubric(
            check_accuracy=CheckpointResult(passed=True, reason="OK"),
            check_persona_language=CheckpointResult(passed=True, reason="OK"),
            check_no_unexplained_jargon=CheckpointResult(passed=True, reason="OK"),
            check_teaches_by_analogy=CheckpointResult(passed=True, reason="OK"),
            check_core_pillars=CheckpointResult(passed=True, reason="OK"),
            check_coherent_flow=CheckpointResult(passed=True, reason="OK"),
        )
        state_pass: AgentState = {
            "evaluation": passing_rubric,
            "revision_count": 0,
        }  # type: ignore
        self.assertEqual(evaluation_router(state_pass), "ship_lesson")

        # Case 2: Failed & revision_count < 2 -> regenerate
        failing_rubric = LessonRubric(
            check_accuracy=CheckpointResult(passed=False, reason="Inaccurate"),
            check_persona_language=CheckpointResult(passed=True, reason="OK"),
            check_no_unexplained_jargon=CheckpointResult(passed=True, reason="OK"),
            check_teaches_by_analogy=CheckpointResult(passed=True, reason="OK"),
            check_core_pillars=CheckpointResult(passed=True, reason="OK"),
            check_coherent_flow=CheckpointResult(passed=True, reason="OK"),
        )
        state_retry: AgentState = {
            "evaluation": failing_rubric,
            "revision_count": 0,
        }  # type: ignore
        self.assertEqual(evaluation_router(state_retry), "regenerate")

        # Case 3: Failed & revision_count >= 2 -> max_retries_reached
        state_max_retry: AgentState = {
            "evaluation": failing_rubric,
            "revision_count": 2,
        }  # type: ignore
        self.assertEqual(evaluation_router(state_max_retry), "max_retries_reached")


if __name__ == "__main__":
    unittest.main()
