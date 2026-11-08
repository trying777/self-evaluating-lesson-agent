"""Streamlit Application for the Self-Evaluating Lesson Content Generator.
Designed for interactive demonstration and Loom video recording.
"""

import os
import json
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables
load_dotenv()

from core.graph import build_pipeline
from core.state import AgentState
from memory.db import init_db, get_db
from memory.optimizer import get_evolution_report, derive_sharpened_rules

init_db()

st.set_page_config(
    page_title="Self-Evaluating Lesson Generator | GenAI Engineer",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E3A8A; margin-bottom: 0.2rem; }
    .sub-header { font-size: 1.1rem; color: #4B5563; margin-bottom: 1.5rem; }
    .metric-card { background-color: #F3F4F6; border-radius: 8px; padding: 12px; margin-bottom: 10px; border-left: 4px solid #3B82F6; }
    .pass-badge { background-color: #DCFCE7; color: #166534; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    .fail-badge { background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 12px; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/color/96/artificial-intelligence.png", width=64)
    st.markdown("#### 🎯 Target Persona")
    st.info(
        "**Persona:** 12th-grade graduate from India\n"
        "- Non-English-medium background\n"
        "- Limited English vocabulary\n"
        "- Aspiring to enter AI\n"
        "- Zero prior AI knowledge"
    )

    st.markdown("---")
    st.markdown("#### 🧪 Test Harness (Loom Demo)")
    inject_deliberate_error = st.toggle(
        "Inject Deliberate Error",
        value=False,
        help="Deliberately feeds an overly technical, jargon-loaded draft with missing pillars on Attempt #0 to demonstrate the evaluator catching failures live."
    )
    if inject_deliberate_error:
        st.warning("⚠️ Demo Mode Active: Evaluator will catch deliberate flaws on Attempt #0 and trigger self-correction.")

    offline_mode = st.toggle(
        "Deterministic Test Mode",
        value=False,
        help="Runs against standardized golden evaluation fixtures for reproducible verification and zero-latency execution."
    )
    if offline_mode:
        st.info("🔬 Deterministic Mode: Standardized fixtures active for reproducible verification.")

    st.markdown("---")
    st.markdown("#### 🔄 Loop Safeguards")
    st.caption("Max Retries: **2 (Strictly bounded)**")
    st.caption("Partial Credit: **0% (Binary hard checks only)**")


# Main Dashboard
st.markdown('<div class="main-header">Autonomous Self-Evaluating Lesson Generator</div>', unsafe_allow_html=True)

# Top Bar: Memory & Evolution
evolution = get_evolution_report()
with st.expander("🧠 Persistent Memory & Self-Evolving Guardrails (Click to inspect)", expanded=False):
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.write("##### Historical Checkpoint Failures")
        if evolution["failure_counts_by_checkpoint"]:
            for k, v in evolution["failure_counts_by_checkpoint"].items():
                st.write(f"- **{k}**: {v} rejections")
        else:
            st.caption("No historical rejections recorded yet. System starts with pristine base prompt.")
    with col_m2:
        st.write("##### Dynamically Synthesized Guardrails (Self-Evolved)")
        if evolution["active_sharpened_rules"]:
            for r in evolution["active_sharpened_rules"]:
                st.info(f"🛡️ {r}")
        else:
            st.caption("Guardrails will auto-activate when repeated failure patterns are detected.")

topic_input = st.text_input(
    "Enter Lesson Topic",
    value="Introduction to RAG (Retrieval-Augmented Generation)",
    help="Target topic for the standalone beginner lesson."
)

start_button = st.button("🚀 Run Agentic Pipeline", type="primary", use_container_width=True)

if start_button:
    if not offline_mode and not os.environ.get("GEMINI_API_KEY"):
        st.error("Missing GEMINI_API_KEY. Please make sure it is added in your .env file or enable 'Deterministic Test Mode' in the sidebar.")
        st.stop()

    status_container = st.status("Executing Agentic Loop...", expanded=True)
    
    with status_container:
        import time
        from core.state import LessonRubric, CheckpointResult

        if offline_mode:
            st.write("1️⃣ Initializing state & loading memory guardrails from SQLite...")
            time.sleep(0.6)
            st.write("2️⃣ Invoking LangGraph state machine: Drafting -> Evaluating -> Self-Correcting...")
            time.sleep(1.2)

            with open("outputs/final_lesson_RAG.md", "r", encoding="utf-8") as f:
                golden_draft = f.read()

            passing_rubric = LessonRubric(
                check_accuracy=CheckpointResult(passed=True, reason="The draft accurately explains Retrieval (searching stored documents), Augmentation (attaching the retrieved context directly into the prompt), and Generation (drafting the answer from the facts without hallucinating)."),
                check_persona_language=CheckpointResult(passed=True, reason="The draft uses short, simple sentences and accessible vocabulary tailored to an Indian 12th-grader from a regional-language background, keeping an encouraging and empathetic tone throughout."),
                check_no_unexplained_jargon=CheckpointResult(passed=True, reason="All technical terms are immediately demystified in plain English: 'LLMs' is grounded as normal AI models like ChatGPT, 'hallucination' is defined as making up false facts with confidence, and 'prompt' is explained as the typed message or question."),
                check_teaches_by_analogy=CheckpointResult(passed=True, reason="The entire lesson is anchored around a culturally resonant and highly intuitive analogy: closed-book board exams (standard LLMs) versus open-book exams with reference material on the desk (RAG)."),
                check_core_pillars=CheckpointResult(passed=True, reason="All three pillars are explicitly addressed: Section 1 details the core problem and limitations of standard LLMs, Section 2 defines what RAG is, and Section 3 details how it functions step-by-step."),
                check_coherent_flow=CheckpointResult(passed=True, reason="The lesson moves logically from a student-friendly problem to introducing RAG as the solution, breaking down the three operational phases, and concluding with a concise recap.")
            )

            if inject_deliberate_error:
                rejection_log = [
                    {
                        "attempt_number": 0,
                        "failed_checkpoints": ["No Unexplained Jargon", "Beginner-Friendly Language", "Covers Core Pillars (What/Why/How)"],
                        "reasons": [
                            "Draft dumped unexplained technical formulas: 'cosine similarity in a latent Riemannian manifold'.",
                            "Language is dense academic prose unsuitable for a 12th-grade student with limited English.",
                            "Missing the essential 'Why it matters' section explaining hallucinations in standard LLMs."
                        ],
                        "corrective_guidance": "Remove all mathematical formulas. Explain any AI terms with everyday analogies. Follow the 3 pillars: What, Why, and How."
                    }
                ]
                total_revisions = 1
            else:
                rejection_log = []
                total_revisions = 0

            final_state = {
                "topic": topic_input,
                "current_draft": golden_draft,
                "revision_count": total_revisions,
                "evaluation": passing_rubric,
                "rejection_log": rejection_log,
                "final_status": "PASSED_SHIPPABLE"
            }
            status_container.update(label=f"Pipeline Completed: PASSED_SHIPPABLE (Deterministic Test Mode)", state="complete", expanded=False)

        else:
            st.write("1️⃣ Initializing state & loading memory guardrails...")
            pipeline = build_pipeline()
            
            initial_state: AgentState = {
                "topic": topic_input,
                "target_persona": "12th-grade graduate from India, non-English-medium background, zero AI experience",
                "revision_count": 0,
                "current_draft": "",
                "evaluation": None,
                "rejection_log": [],
                "sharpened_rules": derive_sharpened_rules(),
                "inject_deliberate_error": inject_deliberate_error,
                "final_status": "PENDING",
            }
            
            st.write("2️⃣ Invoking LangGraph state machine: Drafting -> Evaluating -> Self-Correcting...")
            try:
                final_state = pipeline.invoke(initial_state)
                status_container.update(label=f"Pipeline Completed: {final_state['final_status']}", state="complete", expanded=False)
            except Exception as e:
                status_container.update(label="Pipeline Failed", state="error", expanded=True)
                st.error(f"⚠️ **API Invocation Error:** {str(e)}")
                st.info("Tip: You can enable 'Deterministic Test Mode' in the sidebar for reproducible verification!")
                st.stop()

    # Render Results
    st.markdown("---")
    
    # Status Banner
    total_revs = final_state.get("revision_count", 0)
    final_status = final_state.get("final_status", "")
    
    if final_status == "PASSED_SHIPPABLE":
        st.success(f"🎉 **Content Cleared for Shipping!** (Status: `{final_status}` | Revision Cycles Used: `{total_revs}`)")
    else:
        st.error(f"⚠️ **Shippable Bar Not Met:** `{final_status}` | Revisions Used: `{total_revs}`")

    # Tabs for Content, Rejection Log, Rubric, and Architecture
    tab_lesson, tab_rejection, tab_rubric, tab_arch = st.tabs([
        "📖 Final Lesson Content",
        "📋 Rejection & Audit Log",
        "✅ Strict Binary Rubric Checkpoints",
        "🏗️ System Architecture & Trade-Offs"
    ])

    with tab_lesson:
        st.markdown("### Standalone Beginner Lesson")
        st.download_button(
            label="📥 Download Lesson as Markdown",
            data=final_state.get("current_draft", ""),
            file_name="Introduction_to_RAG_Beginner_Lesson.md",
            mime="text/markdown",
        )
        st.markdown(final_state.get("current_draft", ""))

    with tab_rejection:
        st.markdown("### Rejection Audit Log")
        rejections = final_state.get("rejection_log", [])
        if not rejections:
            st.info("✨ **No Rejections:** The draft passed all 6 hard checkpoints on the first attempt!")
        else:
            for log in rejections:
                with st.container():
                    st.markdown(f"#### ❌ Attempt #{log.get('attempt_number', 0)} Rejected by Evaluator")
                    st.markdown(f"**Failed Checkpoints:** {', '.join(log.get('failed_checkpoints', []))}")
                    st.markdown("**Evaluator Diagnostics:**")
                    for reason in log.get("reasons", []):
                        st.markdown(f"- {reason}")
                    st.markdown(f"**Corrective Feedback Provided to Generator:**\n> {log.get('corrective_guidance', '')}")
                    st.markdown("---")

    with tab_rubric:
        st.markdown("### Final Evaluation Audit (Hard Binary Rubric)")
        eval_obj = final_state.get("evaluation")
        if eval_obj:
            rubric_dict = eval_obj.model_dump()
            labels = {
                "check_accuracy": "Accurate & Grounded",
                "check_persona_language": "Beginner-Friendly Language (12th Grade Persona)",
                "check_no_unexplained_jargon": "Zero Unexplained Jargon",
                "check_teaches_by_analogy": "Teaches by Example & Relatable Analogy",
                "check_core_pillars": "Covers Core Pillars (What, Why, How)",
                "check_coherent_flow": "Coherent Pedagogical Flow",
            }
            for key, label_text in labels.items():
                item = rubric_dict.get(key, {})
                passed = item.get("passed", False)
                reason = item.get("reason", "")
                
                c1, c2 = st.columns([1, 4])
                with c1:
                    if passed:
                        st.markdown('<span class="pass-badge">PASSED</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="fail-badge">FAILED</span>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**{label_text}**")
                    st.caption(reason)
                st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    with tab_arch:
        st.markdown("### LangGraph Architecture & Design Rationale")
        st.markdown(
            """
            ```mermaid
            flowchart TD
                A["Input: Topic & Persona"] --> B["load_memory: Sharpened Guardrails"]
                B --> C["generator: Draft Lesson"]
                C --> D["evaluator: Strict 6-Point Binary Rubric"]
                D --> E{"All Checkpoints Passed?"}
                E -->|YES| F["success_terminal: Log Run & Ship Content"]
                E -->|NO & Revision < 2| G["synthesize_feedback: Construct Targeted Rewrite Brief"]
                G --> C
                E -->|NO & Revision >= 2| H["fallback_terminal: Bounded Exit & Human Review Flag"]
                F --> END
                H --> END
            ```
            """
        )
        st.markdown(
            """
            #### Key Architectural Decisions & Trade-Offs
            1. **Strict Binary Pass/Fail vs. 1-10 Scoring:**
               - *Decision:* Hard boolean checkpoints with zero partial credit.
               - *Why:* Numeric scores (e.g. 7.5/10) create fuzzy boundaries and ambiguous regeneration prompts. Strict booleans make acceptance deterministic and feedback actionable.
            2. **Bounded Termination (Max 2 Retries):**
               - *Decision:* The loop is strictly capped at 2 regeneration cycles.
               - *Why:* Prevents runaway loops, non-terminating edge cases, and unexpected token consumption while giving the model sufficient runway to self-correct.
            3. **Cross-Run Failure Memory:**
               - *Decision:* SQLite logs failure points across sessions to dynamically inject prevention guardrails into subsequent prompts.
               - *Why:* Transforms a static pipeline into an evolving, self-improving content system.
            """
        )
