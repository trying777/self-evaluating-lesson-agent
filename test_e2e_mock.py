"""End-to-end workflow simulation test with deterministic mock LLMs.
Ensures the full Generate -> Evaluate -> Feedback -> Regenerate -> Ship cycle works flawlessly offline.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.state import AgentState, LessonRubric, CheckpointResult
from core.graph import build_pipeline
from memory.db import init_db, get_db

TEST_DB = Path("test_e2e_memory.db")


class TestEndToEndAgentLoop(unittest.TestCase):

    def setUp(self):
        init_db(TEST_DB)

    def tearDown(self):
        try:
            if TEST_DB.exists():
                TEST_DB.unlink()
        except PermissionError:
            pass

    @patch("core.generator.get_llm")
    @patch("core.evaluator.get_evaluator_llm")
    def test_full_generate_evaluate_regenerate_cycle(self, mock_get_eval_llm, mock_get_gen_llm):
        """
        Simulates:
        - Attempt 0: Generator produces a draft with technical jargon.
        - Evaluator catches it: fails check_no_unexplained_jargon.
        - Graph branches to synthesize_feedback: generates critique.
        - Attempt 1: Generator produces a corrected beginner-friendly draft.
        - Evaluator passes all 6 checkpoints.
        - Graph branches to success_terminal: completes with PASSED_SHIPPABLE!
        """
        # Mock Generator Responses
        gen_mock_response_0 = MagicMock()
        gen_mock_response_0.content = "Draft 0: RAG uses vector dot-products."

        gen_mock_response_1 = MagicMock()
        gen_mock_response_1.content = (
            "# Introduction to RAG\n"
            "Imagine writing an exam with an open textbook by your side..."
        )

        mock_gen_llm = MagicMock()
        mock_gen_llm.invoke.side_effect = [gen_mock_response_0, gen_mock_response_1]
        mock_get_gen_llm.return_value = mock_gen_llm

        # Mock Evaluator Responses
        # Evaluation 0: Fail on Jargon
        eval_result_0 = LessonRubric(
            check_accuracy=CheckpointResult(passed=True, reason="Accurate"),
            check_persona_language=CheckpointResult(passed=True, reason="Simple"),
            check_no_unexplained_jargon=CheckpointResult(passed=False, reason="Unexplained 'vector dot-products'"),
            check_teaches_by_analogy=CheckpointResult(passed=True, reason="OK"),
            check_core_pillars=CheckpointResult(passed=True, reason="OK"),
            check_coherent_flow=CheckpointResult(passed=True, reason="OK"),
        )

        # Evaluation 1: All Passed
        eval_result_1 = LessonRubric(
            check_accuracy=CheckpointResult(passed=True, reason="Accurate"),
            check_persona_language=CheckpointResult(passed=True, reason="Simple conversational English"),
            check_no_unexplained_jargon=CheckpointResult(passed=True, reason="All jargon explained with analogies"),
            check_teaches_by_analogy=CheckpointResult(passed=True, reason="Used open-book exam analogy"),
            check_core_pillars=CheckpointResult(passed=True, reason="Covers What, Why, How"),
            check_coherent_flow=CheckpointResult(passed=True, reason="Natural flow"),
        )

        mock_eval_llm = MagicMock()
        mock_eval_llm.invoke.side_effect = [eval_result_0, eval_result_1]
        mock_get_eval_llm.return_value = mock_eval_llm

        # Execute Pipeline
        pipeline = build_pipeline()

        initial_state: AgentState = {
            "topic": "Introduction to RAG",
            "target_persona": "12th-grade graduate from India",
            "revision_count": 0,
            "current_draft": "",
            "evaluation": None,
            "rejection_log": [],
            "sharpened_rules": [],
            "inject_deliberate_error": False,
            "final_status": "PENDING",
        }

        final_state = pipeline.invoke(initial_state)

        # Assertions
        self.assertEqual(final_state["final_status"], "PASSED_SHIPPABLE")
        self.assertEqual(final_state["revision_count"], 1)
        self.assertEqual(len(final_state["rejection_log"]), 1)
        self.assertEqual(final_state["rejection_log"][0]["failed_checkpoints"], ["No Unexplained Jargon"])
        self.assertTrue(final_state["evaluation"].all_passed)
        self.assertIn("open textbook", final_state["current_draft"])


if __name__ == "__main__":
    unittest.main()
