# Self-Evaluating Lesson Content Generator

An autonomous agentic system built with **LangGraph** that generates beginner AI lessons, evaluates them against a strict binary pass/fail rubric, and self-corrects using a bounded retry loop and persistent cross-run memory.

---

## 🚀 Quick Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Free Google Gemini API Key from [Google AI Studio](https://aistudio.google.com/)

### 2. Clone the Repository
```bash
git clone https://github.com/trying777/self-evaluating-lesson-agent.git
```

### 3. Navigate into the Project Directory
```bash
cd self-evaluating-lesson-agent
```

### 4. Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
```

### 5. Activate the Virtual Environment (Windows PowerShell)
```powershell
.\venv\Scripts\Activate.ps1
```

*(For Command Prompt, use `venv\Scripts\activate.bat`; for macOS/Linux, use `source venv/bin/activate`)*

### 6. Install Dependencies
```bash
pip install -r requirements.txt
```

### 7. Configure Environment Variables
Create a `.env` file in the project root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

*(You can also copy the provided template: `cp .env.example .env`)*

---

## 💻 How to Run

### 1. Interactive Web UI (Streamlit)
Launch the interactive web dashboard:

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser. The dashboard includes:
- **Persistent Memory & Self-Evolved Guardrails:** Live inspector displaying historical failure statistics and dynamically synthesized prompt guardrails from SQLite.
- **Test Harness Toggle:** "Inject Deliberate Error" switch to demonstrate the evaluator catching flaws on Attempt #0 and self-correcting on Attempt #1.
- **Tab 1 (Final Lesson Content):** Displays the rendered beginner lesson with a one-click Markdown download button.
- **Tab 2 (Rejection & Audit Log):** Detailed audit trail of failed checkpoints, line diagnostics, and corrective rewrite guidance.
- **Tab 3 (Strict Binary Rubric Checkpoints):** Hard `PASSED`/`FAILED` quality gates across all 6 rubric dimensions with detailed justifications.
- **Tab 4 (System Architecture & Trade-Offs):** Interactive workflow diagram and design decision rationales.

### 2. CLI Execution

Run standard generation for a topic:
```bash
python main.py --topic "Introduction to RAG (Retrieval-Augmented Generation)"
```

Run with deliberate error injection to observe evaluator rejection and self-correction live in terminal:
```bash
python main.py --inject-error
```

Output files are automatically exported to the `outputs/` folder:
- `outputs/final_lesson_RAG.md` (shippable lesson)
- `outputs/rejection_audit_log.json` (audit trail)

---

## 🧪 Running Tests

Run the test suite to verify the pipeline components:

Run unit tests (Pydantic rubric validation, SQLite persistence, and LangGraph routing logic):
```bash
python test_pipeline.py
```

Run end-to-end simulation test (verifies the complete Generate $\to$ Evaluate $\to$ Feedback $\to$ Regenerate $\to$ Ship cycle offline):
```bash
python test_e2e_mock.py
```

---

## 🏗️ Architecture & Workflow

```mermaid
flowchart TD
    Start([Topic Input]) --> Memory[load_memory: Query past failures & load guardrails]
    Memory --> Gen[generator: Draft lesson with persona grounding]
    Gen --> Eval[evaluator: Strict 6-point binary rubric]
    
    Eval --> Router{All Checkpoints Passed?}
    
    Router -->|YES| Success[success_terminal: Log run to SQLite & ship lesson]
    Router -->|NO & Revision < 2| Feedback[synthesize_feedback: Package rewrite critique]
    Feedback --> Gen
    Router -->|NO & Revision >= 2| Fallback[fallback_terminal: Bounded exit & flag for review]
    
    Success --> END([Final Shippable Output])
    Fallback --> END
```

---

## 📁 Project Structure

```text
self-evaluating-lesson-agent/
├── app.py                  # Streamlit web dashboard for live demo
├── main.py                 # CLI runner with telemetry and export flags
├── requirements.txt        # Frozen dependencies
├── .env.example            # Environment template
├── core/
│   ├── state.py            # TypedDict state and Pydantic binary rubric schema
│   ├── generator.py        # Lesson authoring node with persona constraints
│   ├── evaluator.py        # Strict binary evaluator (zero partial credit)
│   ├── feedback.py         # Rejection logger and feedback synthesizer
│   └── graph.py            # LangGraph state machine with max 2 retries
├── memory/
│   ├── db.py               # SQLite persistence for runs and rejection logs
│   └── optimizer.py        # Analyzes historical failures to sharpen prompts
├── outputs/
│   ├── final_lesson_RAG.md # Benchmark generated lesson
│   └── rejection_audit_log.json
├── test_pipeline.py        # Unit tests
└── test_e2e_mock.py        # End-to-end simulation test
```

---

## 🎯 Key Design Choices

1. **Strict Binary Rubric (No Partial Credit):** Evaluates drafts across 6 Boolean checkpoints (`True`/`False`). Eliminates ambiguous numeric scores.
2. **Bounded Retry Loop:** Capped at a hard limit of **2 retries** to prevent infinite loops and runaway token usage.
3. **Cross-Run Memory & Self-Evolution:** SQLite logs failure modes across runs and dynamically injects prevention guardrails into subsequent prompts.
