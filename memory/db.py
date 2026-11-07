"""SQLite persistence layer for storing evaluation histories, rejection logs, and run telemetry."""

import sqlite3
import json
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional

DEFAULT_DB_PATH = Path("memory.db")


@contextmanager
def get_db(db_path: Path = DEFAULT_DB_PATH):
    """Context manager that ensures the SQLite connection is committed and closed."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Initializes tables for runs, evaluations, and rejection audits."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                target_persona TEXT NOT NULL,
                total_revisions INTEGER NOT NULL,
                final_status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                attempt_number INTEGER NOT NULL,
                check_accuracy INTEGER NOT NULL,
                check_persona_language INTEGER NOT NULL,
                check_no_unexplained_jargon INTEGER NOT NULL,
                check_teaches_by_analogy INTEGER NOT NULL,
                check_core_pillars INTEGER NOT NULL,
                check_coherent_flow INTEGER NOT NULL,
                all_passed INTEGER NOT NULL,
                draft_preview TEXT,
                full_evaluation_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs (id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rejection_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER,
                attempt_number INTEGER NOT NULL,
                failed_checkpoints_json TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                corrective_guidance TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES pipeline_runs (id)
            )
        """)
        conn.commit()


def record_run(
    topic: str,
    target_persona: str,
    total_revisions: int,
    final_status: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Records a run and returns its generated run ID."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO pipeline_runs (topic, target_persona, total_revisions, final_status)
            VALUES (?, ?, ?, ?)
            """,
            (topic, target_persona, total_revisions, final_status),
        )
        return cursor.lastrowid


def record_evaluation(
    run_id: int,
    attempt_number: int,
    rubric_dict: Dict[str, Any],
    draft_text: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Records an individual rubric evaluation pass."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO evaluation_audits (
                run_id, attempt_number,
                check_accuracy, check_persona_language,
                check_no_unexplained_jargon, check_teaches_by_analogy,
                check_core_pillars, check_coherent_flow,
                all_passed, draft_preview, full_evaluation_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                attempt_number,
                1 if rubric_dict.get("check_accuracy", {}).get("passed") else 0,
                1 if rubric_dict.get("check_persona_language", {}).get("passed") else 0,
                1 if rubric_dict.get("check_no_unexplained_jargon", {}).get("passed") else 0,
                1 if rubric_dict.get("check_teaches_by_analogy", {}).get("passed") else 0,
                1 if rubric_dict.get("check_core_pillars", {}).get("passed") else 0,
                1 if rubric_dict.get("check_coherent_flow", {}).get("passed") else 0,
                1 if rubric_dict.get("all_passed") else 0,
                draft_text[:250],
                json.dumps(rubric_dict),
            ),
        )


def record_rejection(
    run_id: int,
    attempt_number: int,
    failed_checkpoints: List[str],
    reasons: List[str],
    corrective_guidance: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Records a rejection event with diagnostic details."""
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO rejection_records (
                run_id, attempt_number, failed_checkpoints_json, reasons_json, corrective_guidance
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_id,
                attempt_number,
                json.dumps(failed_checkpoints),
                json.dumps(reasons),
                corrective_guidance,
            ),
        )


def get_failure_statistics(db_path: Path = DEFAULT_DB_PATH) -> Dict[str, int]:
    """Calculates frequency of failures per checkpoint across historical runs."""
    init_db(db_path)
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT failed_checkpoints_json FROM rejection_records")
        rows = cursor.fetchall()

    stats: Dict[str, int] = {}
    for (row,) in rows:
        try:
            failed_list = json.loads(row)
            for checkpoint in failed_list:
                stats[checkpoint] = stats.get(checkpoint, 0) + 1
        except Exception:
            continue
    return stats
