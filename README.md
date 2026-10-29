# PromptLab — Agentic AI Prompt Testing, Evaluation & Optimization Platform

> **"Find prompt failures, understand why they happen, test improvements automatically, and select the best-performing prompt using measurable evidence."**

PromptLab is a local-first, full-stack AI engineering platform designed to systematically evaluate, benchmark, and optimize LLM prompts using reproducible test suites, Scikit-learn classification metrics, and a bounded agentic optimizer.

---

## 🌟 Key Features

### 1. Interactive Prompt Lab
- Edit system prompts, user templates, and valid label specifications.
- Instant single-example testing with real-time latency, label validation, and reasoning extraction.
- Version history tracking (`v1`, `v2`, `v3`...) with author attribution (Human Manual vs. Agent Mutated).

### 2. Dataset Management & Leakage Prevention
- Pre-seeded 30-sample **Starter Sentiment Classification Benchmark** covering tricky edge cases:
  - Strong positive & negative sentiment
  - Explicit and subtle negation (*"not bad at all"*, *"hardly great"*)
  - Sarcasm & ironic phrasing (*"just what I needed, another crash"*)
  - Mixed sentiment with contrasting clauses (*"ambiance was lovely, but pasta was undercooked"*)
  - Neutral / ambiguous inquiries (*"store closes at 9 PM"*)
- CSV and JSON dataset uploader with configurable column mappings.
- **Strict Data Isolation**: Automatic 70/30 deterministic partition into **Tuning Split** (for agent failure analysis and prompt mutation) and **Held-Out Split** (unbiased testing partition strictly shielded from candidate generation).

### 3. Systematic Evaluation Engine
- Independent, reusable evaluation runner.
- Comprehensive telemetry:
  - Classification accuracy & error rate
  - Scikit-learn macro precision, recall, and F1 score
  - Full $N \times N$ interactive **Confusion Matrix** with off-diagonal failure highlighting
  - Latency profiling: Average, Median, and P95 latency (ms)
  - Detailed example-level failure audit (input text, expected label, actual prediction, latency)
- Single-click CSV and JSON export of evaluation runs and experiment archives.

### 4. Bounded Agentic Optimizer
- Autonomous prompt mutation engine with bounded iterations (1–6 cycles) and cycle detection.
- **Scientific Optimization Loop**:
  1. **Inspect Failures**: Audits error cases on the tuning split and identifies patterns (e.g., negation blindness, sarcasm misclassification, verbosity).
  2. **Formulate Hypothesis**: Generates evidence-backed hypotheses for why the model failed.
  3. **Select Mutation Strategy**: Applies targeted strategies (`explicit_negation_rules`, `few_shot_examples`, `format_constraint`, `chain_of_thought`).
  4. **Evaluate Candidate**: Runs a fresh evaluation against the tuning split.
  5. **Pairwise Comparison & Decision**: Compares candidate against baseline according to chosen objective (`maximize_accuracy`, `minimize_invalid_outputs`, `minimize_latency_with_threshold`, `balanced`). Accepts improving candidates or rejects regressions.
  6. **Held-Out Final Verification**: Evaluates the accepted champion prompt against the unseen held-out split to verify real-world generalization.
- Strictly typed tool registry with full execution logging (`agent_tool_logs`).

---

## 🏛 Architecture

```
promptlab/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI REST endpoints
│   │   │   ├── agent_runs.py     # Optimizer launch and status
│   │   │   ├── dashboard.py      # Telemetry & trends
│   │   │   ├── datasets.py       # Dataset upload, preview & partitioning
│   │   │   ├── evaluations.py    # Benchmark evaluations & comparisons
│   │   │   ├── experiments.py    # Experiment & prompt versioning
│   │   │   ├── export.py         # CSV & JSON report downloads
│   │   │   ├── health.py         # System health & LLM diagnostics
│   │   │   └── prompts.py        # Prompt creation & playground
│   │   ├── agent_engine.py       # Bounded Agentic Optimizer
│   │   ├── agent_tools.py        # Typed tool registry
│   │   ├── config.py             # App settings & environment variables
│   │   ├── database.py           # SQLite WAL persistence schema (9 tables)
│   │   ├── dataset_service.py    # Benchmark seeding & dataset partitioning
│   │   ├── evaluation_engine.py  # Scikit-learn metrics & latency tracking
│   │   ├── failure_analysis.py   # Error categorization & hypothesis engine
│   │   ├── llm_client.py         # Ollama client + deterministic mock fallback
│   │   ├── main.py               # FastAPI application entry point
│   │   └── metrics.py            # Label parsers & statistical calculations
│   ├── data/
│   │   └── starter_sentiment.json # 30 benchmark examples
│   ├── tests/                    # Pytest test suite (17 tests)
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.js         # Frontend REST API client
│   │   ├── components/
│   │   │   └── Navigation.jsx    # Sidebar navigation & model status
│   │   ├── views/
│   │   │   ├── DashboardView.jsx # High-level stats, charts & regressions
│   │   │   ├── PromptLabView.jsx # Live prompt editor & playground
│   │   │   ├── DatasetsView.jsx  # Dataset manager & partition viewer
│   │   │   ├── EvaluationsView.jsx # Confusion matrix & pairwise comparison
│   │   │   ├── AgentRunsView.jsx # Autonomous optimizer timeline & tool logs
│   │   │   ├── ExperimentsView.jsx # Version history & project exports
│   │   │   └── SettingsView.jsx  # Connectivity diagnostics & environment docs
│   │   ├── App.jsx               # Main application router
│   │   ├── App.test.jsx          # Vitest component test suite
│   │   ├── index.css             # Design system & dark theme styling
│   │   ├── main.jsx              # React 18 DOM mount
│   │   └── setupTests.js         # Vitest polyfills
│   ├── package.json
│   └── vite.config.js
├── .env.example
├── .gitignore
└── README.md
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.12)
- **Node.js 18+** (Tested on Node.js v25)
- Optional: **Ollama** with `llama3.2:1b` (runs out-of-the-box with deterministic mock mode if Ollama is not installed)

---

### Backend Setup

1. **Navigate to the backend directory**:
   ```powershell
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the backend test suite**:
   ```powershell
   pytest -v
   ```
   *All 17 tests verify metric computation, dataset partitioning, failure analysis, and bounded agent optimization.*

5. **Start the FastAPI server**:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Interactive API documentation will be available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

### Frontend Setup

1. **Navigate to the frontend directory**:
   ```powershell
   cd frontend
   ```

2. **Install frontend dependencies**:
   ```powershell
   npm install
   ```

3. **Run frontend tests**:
   ```powershell
   npm test
   ```

4. **Start the Vite development server**:
   ```powershell
   npm run dev
   ```
   Open your browser at [http://localhost:5173](http://localhost:5173).

5. **Build for production**:
   ```powershell
   npm run build
   ```

---

## ⚙️ Configuration & Environment Variables

Copy `.env.example` to create your local `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MOCK_LLM` | `true` | When `true`, uses instant deterministic mock LLM for offline testing without network/Ollama. Set to `false` for live Ollama inference. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Base URL of your local Ollama instance. |
| `DEFAULT_MODEL` | `llama3.2:1b` | Default model used for prompt evaluation and mutation. |
| `DATABASE_PATH` | `./promptlab.db` | File path for persistent SQLite database. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed origins for web browser requests. |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend API URL used by the frontend. |

---

## 🧠 Using Local Ollama

To run real LLM inference with Ollama on your Windows laptop:

1. Download and install Ollama from [ollama.ai](https://ollama.ai).
2. Pull the recommended lightweight model:
   ```powershell
   ollama run llama3.2:1b
   ```
3. Set `MOCK_LLM=false` in your `.env` or run the backend with:
   ```powershell
   $env:MOCK_LLM="false"; uvicorn app.main:app --port 8000
   ```
4. Check the **Settings & Diagnostics** page in PromptLab to verify that the status dot switches to green (**Ollama Online**).

---

## 🔒 Security & Data Privacy

- **Local-First Processing**: In both local Ollama mode and mock mode, all prompt evaluations run strictly on your machine. No user prompts or dataset contents are sent to third-party cloud APIs.
- **Deterministic Seed Mocking**: In restricted sandbox environments or offline mode, the deterministic mock engine enables full test suite execution, failure categorization, and agent cycles without requiring open socket permissions.
- **Dataset Leakage Shield**: Prompt optimization is bounded strictly to the `train` partition. The held-out `test` partition is isolated from error inspection tools.

---

## 🌐 Deployment Options

### Frontend (Vercel)
The frontend is built with standard Vite and React and is ready for Vercel deployment:
- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL` set to your backend's public or bridged URL.

### Backend
The backend can be run on any standard Linux or Windows host, or in Docker:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## ⚖️ Limitations & Realistic Trade-offs

- **Small Dataset Generalization**: High accuracy on a 30-example starter benchmark does not prove universal real-world performance across different domains. Users should upload representative domain datasets.
- **Local Model Capacity**: Lightweight models like `llama3.2:1b` run fast on low-RAM laptops, but complex multi-turn logic may require larger quantized models (`llama3.1:8b` or `mistral:7b`).
- **Deterministic Label Matching**: Classification metrics evaluate label conformance and format adherence; they do not assess subjective or stylistic nuances beyond defined constraints.

---

## 📄 License
MIT License. Built for agentic AI engineering, testing, and evaluation.
