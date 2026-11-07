"""CLI Runner for the Self-Evaluating Lesson Generator."""

import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (.env)
load_dotenv()

from core.graph import build_pipeline
from core.state import AgentState
from memory.db import init_db
from memory.optimizer import get_evolution_report


def run_cli():
    parser = argparse.ArgumentParser(
        description="Self-Evaluating Lesson Content Generator for AI Education"
    )
    parser.add_argument(
        "--topic",
        type=str,
        default="Introduction to RAG (Retrieval-Augmented Generation)",
        help="The topic to generate a beginner lesson for.",
    )
    parser.add_argument(
        "--inject-error",
        action="store_true",
        help="Inject a deliberate error in draft 0 to demonstrate evaluator rejection.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Directory to save exported lesson and rejection logs.",
    )

    args = parser.parse_args()

    # Verify API key
    if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        print("\n[ERROR] Missing GEMINI_API_KEY or GOOGLE_API_KEY.")
        print("Please set it in your environment or in a .env file:")
        print("  GEMINI_API_KEY=your_key_here\n")
        sys.exit(1)

    init_db()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("🤖 SELF-EVALUATING LESSON CONTENT GENERATOR")
    print("=" * 70)
    print(f"Topic: {args.topic}")
    print(f"Target Persona: 12th-grade graduate from India (non-English medium)")
    print(f"Deliberate Error Injection: {'ENABLED (Demo Mode)' if args.inject_error else 'DISABLED'}")

    # Inspect evolutionary memory
    evolution = get_evolution_report()
    if evolution["active_sharpened_rules"]:
        print(f"\n[MEMORY] Loaded {len(evolution['active_sharpened_rules'])} self-evolved guardrail(s) from past failures:")
        for r in evolution["active_sharpened_rules"]:
            print(f"  • {r}")
    else:
        print("\n[MEMORY] Memory initialized. No historical failure patterns detected yet.")

    print("\n[PIPELINE] Compiling LangGraph workflow...")
    pipeline = build_pipeline()

    initial_state: AgentState = {
        "topic": args.topic,
        "target_persona": "12th-grade graduate from India, non-English-medium background, zero AI experience",
        "revision_count": 0,
        "current_draft": "",
        "evaluation": None,
        "rejection_log": [],
        "sharpened_rules": [],
        "inject_deliberate_error": args.inject_error,
        "final_status": "PENDING",
    }

    print("\n[PIPELINE] Executing autonomous Generate -> Evaluate -> Regenerate loop...")
    result = pipeline.invoke(initial_state)

    print("\n" + "=" * 70)
    print(f"🏁 EXECUTION FINISHED: {result['final_status']}")
    print(f"Total Revision Cycles Used: {result['revision_count']}")
    print("=" * 70)

    # Display Rejection Log if retries occurred
    if result["rejection_log"]:
        print("\n📋 AUDIT / REJECTION LOG:")
        for idx, entry in enumerate(result["rejection_log"], 1):
            print(f"\n--- Attempt #{entry['attempt_number']} (REJECTED) ---")
            print(f"Failed Checkpoints: {', '.join(entry['failed_checkpoints'])}")
            print("Reasons:")
            for r in entry['reasons']:
                print(f"  ❌ {r}")
            print(f"Corrective Guidance Passed to Generator:\n  💡 {entry['corrective_guidance']}")
    else:
        print("\n✨ Passed all checkpoints on Attempt #0 with ZERO rejections!")

    # Display Final Evaluator Checklist
    if result.get("evaluation"):
        print("\n📊 FINAL RUBRIC EVALUATION CHECKLIST (Strict Binary):")
        eval_dict = result["evaluation"].model_dump()
        check_labels = {
            "check_accuracy": "Accurate & Grounded",
            "check_persona_language": "Beginner-Friendly Language",
            "check_no_unexplained_jargon": "No Unexplained Jargon",
            "check_teaches_by_analogy": "Teaches by Analogy/Example",
            "check_core_pillars": "Covers Key Points (What/Why/How)",
            "check_coherent_flow": "Coherent Teaching Flow",
        }
        for key, label in check_labels.items():
            check_data = eval_dict.get(key, {})
            status = "✅ PASS" if check_data.get("passed") else "❌ FAIL"
            print(f"  {status} | {label}: {check_data.get('reason')}")

    # Export Files
    lesson_path = output_dir / "final_lesson_RAG.md"
    rejection_path = output_dir / "rejection_audit_log.json"

    with open(lesson_path, "w", encoding="utf-8") as f:
        f.write(result["current_draft"])

    with open(rejection_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "topic": args.topic,
                "final_status": result["final_status"],
                "total_revisions": result["revision_count"],
                "rejection_log": result["rejection_log"],
                "evaluation_checklist": result["evaluation"].model_dump() if result.get("evaluation") else {},
            },
            f,
            indent=2,
        )

    print(f"\n📁 Exported Shippable Lesson -> {lesson_path}")
    print(f"📁 Exported Rejection Audit Log -> {rejection_path}")
    print("\n" + "=" * 70)


if __name__ == "__main__":
    run_cli()
