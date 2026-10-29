# PromptLab — Agentic AI Prompt Testing, Evaluation & Optimization Platform

> **"Find prompt failures, understand why they happen, test improvements automatically, and select the best-performing prompt using measurable evidence."**

PromptLab is a full-stack, local-first AI engineering platform designed to systematically evaluate, benchmark, and optimize LLM prompts using reproducible test suites, Scikit-learn classification metrics, and a bounded agentic optimizer.

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
│   │   │   ├── agent_runs.py     # Optimizer launch, polling, and logs
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
│   ├── tests/                    # Pytest test suite (18 automated tests)
│   ├── Dockerfile                # Production container specification
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
│   ├── vercel.json               # Vercel configuration for frontend/ root
│   └── vite.config.js
├── .env.example                  # Environment configuration template
├── .gitignore                    # Production git exclusions
├── vercel.json                   # Vercel configuration for repo root
└── README.md
```

---

## 🚀 Quickstart Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.12)
- **Node.js 18+** (Tested on Node.js v25)
- Optional: **Ollama** with `llama3.2:1b` (runs out-of-the-box with deterministic mock mode if Ollama is not installed)

---

### Backend Setup (Windows PowerShell)

1. **Navigate to the backend directory**:
   ```powershell
   cd backend
   ```

2. **Create and activate a virtual environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install backend dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Run the backend test suite**:
   ```powershell
   pytest -v tests
   ```
   *All 18 tests run with deterministic offline mocks and verify metrics, partitioning, and agent workflow in <5 seconds.*

5. **Start the FastAPI backend server**:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *Interactive API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).*

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

3. **Run frontend unit tests**:
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
| `MOCK_LLM` | `false` | When `true`, uses instant deterministic mock LLM for testing without network/Ollama. Set to `false` for live local Ollama inference. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Base URL of your local Ollama instance. |
| `DEFAULT_MODEL` | `llama3.2:1b` | Default model used for prompt evaluation and mutation. |
| `DATABASE_PATH` | `./promptlab.db` | File path for persistent SQLite database. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed origins for web browser requests. In production, add your deployed Vercel URL. |
| `VITE_API_URL` | `http://127.0.0.1:8000` | Backend API URL used by the frontend browser client. |

---

## 🧠 Using Local Ollama

To run real LLM inference with Ollama on your Windows computer:

1. Download and install Ollama from [ollama.ai](https://ollama.ai).
2. Pull the recommended lightweight model:
   ```powershell
   ollama run llama3.2:1b
   ```
3. Set `MOCK_LLM=false` in your `.env`:
   ```powershell
   $env:MOCK_LLM="false"; uvicorn app.main:app --port 8000
   ```
4. Verify live Ollama integration using the verification test:
   ```powershell
   python tests/verify_live_ollama.py
   ```
5. Check the **Settings & Diagnostics** page in PromptLab to verify that the status dot switches to green (**Ollama Online**).

---

## 🌐 Public Deployment Architecture

### 1. Frontend Deployment on Vercel

The frontend is a standard React + Vite single-page application configured with `vercel.json` for seamless routing.

#### Deployment Steps:
1. Push this repository to GitHub.
2. Log into [Vercel](https://vercel.com) and click **"Add New Project"** -> **"Import Git Repository"**.
3. Choose your PromptLab repository.
4. **Project Settings**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: `frontend` (or leave as `.` if using root `vercel.json`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. **Environment Variables**:
   - Add `VITE_API_URL`: Set to your deployed backend URL (e.g., `https://promptlab-api.onrender.com`).
   *Note: Never leave this as `http://127.0.0.1:8000` on a public Vercel deployment, as visitors' browsers cannot reach your local computer.*
6. Click **Deploy**.

---

### 2. Backend Hosting Options

FastAPI requires a persistent Python environment. Recommended deployment targets:

#### Option A: Render / Railway / Fly.io (Container or Python Service)
- **Runtime**: Python 3.12 or Docker (`backend/Dockerfile`).
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Persistent Disk**: Mount a persistent volume at `/app/data` and configure `DATABASE_PATH=/app/data/promptlab.db` so SQLite persists across container restarts.
- **Environment Variables**:
  - `MOCK_LLM`: `false` (if connected to remote Ollama) or `true` (for zero-latency demo mode).
  - `CORS_ORIGINS`: Set to your Vercel frontend URL: `https://your-app.vercel.app`.
  - `OLLAMA_BASE_URL`: URL of your hosted Ollama server or model endpoint.

#### Option B: Local Mode with Vercel Frontend
If you want to run Ollama locally on your GPU/laptop while using a Vercel-hosted frontend:
1. Ensure your local FastAPI backend has `CORS_ORIGINS` set to include `https://your-app.vercel.app`.
2. Configure `VITE_API_URL=http://localhost:8000` in Vercel for development/local access, or use a secure tunnel (e.g. Cloudflare Tunnels with authentication).
*Warning: Never expose an unauthenticated Ollama port directly to the public internet.*

---

## 🔒 Security & Data Privacy

- **Local-First Processing**: In local Ollama mode and mock mode, all prompt evaluations run strictly on your machine. No user prompts or dataset contents are sent to third-party cloud APIs.
- **Dataset Leakage Shield**: Prompt optimization is bounded strictly to the `train` partition. The held-out `test` partition is isolated from error inspection tools.
- **Strict CORS Control**: Unrestricted wildcards (`*`) are disabled in production; only explicitly configured origins are permitted.

---

## 📄 License
MIT License. Built for agentic AI engineering, testing, and evaluation.
