import React, { useState, useEffect } from 'react';
import { 
  Settings as SettingsIcon, 
  Server, 
  Database, 
  ShieldCheck, 
  Cpu, 
  RefreshCw, 
  Terminal, 
  CheckCircle2, 
  AlertCircle,
  Code
} from 'lucide-react';
import { api } from '../api/client';

export function SettingsView() {
  const [health, setHealth] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  useEffect(() => {
    loadHealth();
  }, []);

  async function loadHealth() {
    setRefreshing(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      setHealth({
        status: 'error',
        database: 'offline',
        llm: {
          status: 'offline',
          error: err.message,
          default_model: 'llama3.2:1b'
        }
      });
    } finally {
      setRefreshing(false);
    }
  }

  const isMock = health?.llm?.mode === 'mock_deterministic' || health?.llm?.status === 'mock_mode';
  const isOnline = health?.llm?.status === 'connected';

  const envVars = [
    { key: 'MOCK_LLM', value: 'true', desc: 'When true, uses zero-latency deterministic mock LLM for testing.' },
    { key: 'OLLAMA_BASE_URL', value: 'http://127.0.0.1:11434', desc: 'Base endpoint URL for local Ollama server.' },
    { key: 'DEFAULT_MODEL', value: 'llama3.2:1b', desc: 'Default local model for prompt evaluations and mutations.' },
    { key: 'DATABASE_PATH', value: 'promptlab.db', desc: 'SQLite persistent database file path.' },
    { key: 'CORS_ORIGINS', value: 'http://localhost:5173, http://127.0.0.1:5173', desc: 'Allowed origins for frontend browser communication.' }
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Settings & Diagnostics</h1>
          <p className="page-subtitle">
            Local model connectivity, SQLite persistence status, and runtime environment telemetry.
          </p>
        </div>
        <div>
          <button className="btn btn-secondary" onClick={loadHealth} disabled={refreshing}>
            <RefreshCw size={16} className={refreshing ? 'spin' : ''} />
            Refresh Diagnostics
          </button>
        </div>
      </div>

      {/* Model & Diagnostics Status Grid */}
      <div className="grid-cards" style={{ marginBottom: 24 }}>
        <div className="metric-card">
          <div className="metric-header">
            <span>LLM Execution Engine</span>
            <Cpu size={16} style={{ color: isOnline ? 'var(--success)' : isMock ? 'var(--primary)' : 'var(--danger)' }} />
          </div>
          <div className="metric-value" style={{ fontSize: '1.4rem', color: isOnline ? 'var(--success)' : isMock ? 'var(--primary)' : 'var(--danger)' }}>
            {isOnline ? 'Ollama Online' : isMock ? 'Mock Deterministic' : 'Offline'}
          </div>
          <div className="metric-sub">
            Model: <code style={{ color: 'var(--cyan)' }}>{health?.llm?.default_model || 'llama3.2:1b'}</code>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Database Persistence</span>
            <Database size={16} style={{ color: health?.database === 'connected' ? 'var(--success)' : 'var(--danger)' }} />
          </div>
          <div className="metric-value" style={{ fontSize: '1.4rem', color: 'var(--success)' }}>
            SQLite (WAL)
          </div>
          <div className="metric-sub">
            9 Persistent Tables & Foreign Keys
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Evaluation Framework</span>
            <ShieldCheck size={16} style={{ color: 'var(--cyan)' }} />
          </div>
          <div className="metric-value" style={{ fontSize: '1.4rem' }}>
            Scikit-Learn
          </div>
          <div className="metric-sub">
            Macro F1, Precision, Recall, Confusion Matrix
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>API Server</span>
            <Server size={16} />
          </div>
          <div className="metric-value" style={{ fontSize: '1.4rem' }}>
            FastAPI 0.110+
          </div>
          <div className="metric-sub">
            Pydantic v2 Request Validation
          </div>
        </div>
      </div>

      {/* Local Ollama Setup Instructions */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Server size={18} style={{ color: 'var(--primary)' }} />
            <span>Local Ollama Integration</span>
          </div>
          <span className={`badge ${isOnline ? 'badge-success' : 'badge-warning'}`}>
            {isOnline ? 'Connected' : 'Mock Mode Active'}
          </span>
        </div>

        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 16 }}>
          PromptLab is built for local-first AI development. In standard sandboxed test runs or environments without Ollama running, it automatically uses high-performance deterministic mocking to test all prompt flows, failure inspections, and mutations.
        </p>

        <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Terminal size={14} /> To connect a live local Ollama instance:
          </div>
          <ol style={{ paddingLeft: 20, fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
            <li>Install Ollama from <a href="https://ollama.ai" target="_blank" rel="noreferrer" style={{ color: 'var(--primary)' }}>https://ollama.ai</a></li>
            <li>Pull the recommended lightweight model: <code style={{ background: 'var(--bg-surface)', padding: '2px 6px', borderRadius: 4, color: 'var(--cyan)' }}>ollama run llama3.2:1b</code></li>
            <li>Ensure Ollama is listening on <code style={{ background: 'var(--bg-surface)', padding: '2px 6px', borderRadius: 4, color: 'var(--cyan)' }}>http://127.0.0.1:11434</code></li>
            <li>In your <code style={{ background: 'var(--bg-surface)', padding: '2px 6px', borderRadius: 4 }}>backend/.env</code>, set <code style={{ color: 'var(--cyan)' }}>MOCK_LLM=false</code></li>
          </ol>
        </div>
      </div>

      {/* Database Schema & Tables */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={18} style={{ color: 'var(--cyan)' }} />
            <span>Persistent Database Tables</span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 12 }}>
          {[
            { name: 'experiments', desc: 'Projects, tasks, objectives, default models' },
            { name: 'prompts', desc: 'Versioned prompt templates & mutation authors' },
            { name: 'datasets', desc: 'Benchmark datasets, metadata, content hashes' },
            { name: 'dataset_examples', desc: 'Tuning vs held-out partitioned examples' },
            { name: 'evaluations', desc: 'Benchmark run metrics, accuracy, macro F1, P95' },
            { name: 'evaluation_results', desc: 'Example-level inputs, outputs, errors, latency' },
            { name: 'agent_runs', desc: 'Autonomous optimizer sessions & convergence' },
            { name: 'agent_iterations', desc: 'Hypotheses, strategies, prompt mutations, scores' },
            { name: 'agent_tool_logs', desc: 'Strictly typed tool invocation audit trail' }
          ].map((t) => (
            <div key={t.name} style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 14px' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.85rem' }}>
                {t.name}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                {t.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Environment Variables Reference */}
      <div className="card">
        <div className="card-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Code size={18} style={{ color: 'var(--warning)' }} />
            <span>Environment Configuration (.env)</span>
          </div>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: 200 }}>Variable</th>
                <th style={{ width: 220 }}>Default Value</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {envVars.map((v) => (
                <tr key={v.key}>
                  <td>
                    <code style={{ color: 'var(--cyan)', fontWeight: 600 }}>{v.key}</code>
                  </td>
                  <td>
                    <code style={{ background: 'var(--bg-surface)', padding: '2px 6px', borderRadius: 4, fontSize: '0.8rem' }}>
                      {v.value}
                    </code>
                  </td>
                  <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    {v.desc}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
