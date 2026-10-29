import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Play, 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ArrowRight, 
  ShieldCheck, 
  Sliders, 
  Code, 
  Layers, 
  ChevronDown, 
  ChevronUp, 
  Terminal,
  Activity,
  AlertCircle
} from 'lucide-react';
import { api } from '../api/client';

export function AgentRunsView() {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('');
  const [selectedRun, setSelectedRun] = useState(null);
  const [loading, setLoading] = useState(true);

  // Launch Form
  const [experiments, setExperiments] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedExpId, setSelectedExpId] = useState('');
  const [selectedPromptId, setSelectedPromptId] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [objective, setObjective] = useState('maximize_accuracy');
  const [maxIterations, setMaxIterations] = useState(4);
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState(null);
  const [launchSuccess, setLaunchSuccess] = useState(null);

  // Tool log drawer / accordion
  const [expandedLogId, setExpandedLogId] = useState(null);
  const [expandedStepId, setExpandedStepId] = useState(null);

  useEffect(() => {
    loadRuns();
    loadSetupData();
  }, []);

  useEffect(() => {
    if (selectedRunId) {
      loadRunDetail(selectedRunId);
    }
  }, [selectedRunId]);

  async function loadRuns() {
    setLoading(true);
    try {
      const data = await api.listAgentRuns();
      setRuns(data);
      if (data.length > 0 && !selectedRunId) {
        setSelectedRunId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load agent runs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadSetupData() {
    try {
      const [exps, dss] = await Promise.all([api.listExperiments(), api.listDatasets()]);
      setExperiments(exps);
      setDatasets(dss);
      if (exps.length > 0) {
        setSelectedExpId(exps[0].id);
        const exp = await api.getExperiment(exps[0].id);
        if (exp.prompts && exp.prompts.length > 0) {
          setSelectedPromptId(exp.prompts[0].id);
        }
      }
      if (dss.length > 0) {
        setSelectedDatasetId(dss[0].id);
      }
    } catch (err) {
      console.error('Failed to load setup data:', err);
    }
  }

  async function handleExpChange(expId) {
    setSelectedExpId(expId);
    try {
      const exp = await api.getExperiment(expId);
      if (exp.prompts && exp.prompts.length > 0) {
        setSelectedPromptId(exp.prompts[0].id);
      } else {
        setSelectedPromptId('');
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function loadRunDetail(id) {
    try {
      const run = await api.getAgentRun(id);
      setSelectedRun(run);
    } catch (err) {
      console.error('Failed to load agent run detail:', err);
    }
  }

  async function handleLaunchRun(e) {
    e.preventDefault();
    if (!selectedPromptId || !selectedDatasetId) {
      setLaunchError('Please select both a base prompt and a tuning dataset.');
      return;
    }
    setLaunching(true);
    setLaunchError(null);
    setLaunchSuccess(null);

    try {
      const res = await api.createAgentRun({
        experiment_id: selectedExpId,
        base_prompt_id: selectedPromptId,
        dataset_id: selectedDatasetId,
        objective: objective,
        max_iterations: parseInt(maxIterations, 10),
      });

      setLaunchSuccess(`Optimizer run started! ID: ${res.id}`);
      await loadRuns();
      setSelectedRunId(res.id);

      // Poll run status every 2 seconds until completed
      const pollInterval = setInterval(async () => {
        try {
          const updated = await api.getAgentRun(res.id);
          setSelectedRun(updated);
          if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'stopped') {
            clearInterval(pollInterval);
            await loadRuns();
          }
        } catch (e) {
          clearInterval(pollInterval);
        }
      }, 2000);

    } catch (err) {
      setLaunchError(err.message || 'Failed to start agent run.');
    } finally {
      setLaunching(false);
    }
  }

  const iterations = selectedRun?.iterations || [];
  const toolLogs = selectedRun?.tool_logs || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Agentic Prompt Optimizer</h1>
          <p className="page-subtitle">
            Autonomous, bounded prompt mutation engine with hypothesis-driven strategies and held-out validation.
          </p>
        </div>
      </div>

      {/* Top Banner: Scientific Methodology & Isolation Guarantee */}
      <div style={{ background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.3)', borderRadius: 10, padding: '14px 18px', marginBottom: 24, display: 'flex', alignItems: 'center', gap: 14 }}>
        <ShieldCheck size={28} style={{ color: 'var(--primary)', flexShrink: 0 }} />
        <div>
          <div style={{ fontWeight: 600, color: '#fff', fontSize: '0.9rem' }}>
            Bounded Optimization & Data Isolation Guarantee
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: 2 }}>
            The agent iteratively inspects failure evidence, forms a targeted hypothesis (e.g. negation sensitivity), mutates the prompt, and evaluates strictly against the <strong>Tuning partition</strong>. The <strong>Held-out split</strong> is never seen by the agent during optimization, ensuring reproducible, unbiased validation.
          </div>
        </div>
      </div>

      {/* Launcher Card */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div className="card-title">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={18} style={{ color: 'var(--primary)' }} />
            <span>Launch New Optimizer Session</span>
          </div>
        </div>

        {launchError && (
          <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.85rem' }}>
            {launchError}
          </div>
        )}
        {launchSuccess && (
          <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.85rem' }}>
            {launchSuccess}
          </div>
        )}

        <form onSubmit={handleLaunchRun}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16, marginBottom: 16 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Experiment</label>
              <select
                className="form-select"
                value={selectedExpId}
                onChange={(e) => handleExpChange(e.target.value)}
              >
                {experiments.map((exp) => (
                  <option key={exp.id} value={exp.id}>{exp.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Seed Prompt</label>
              <select
                className="form-select"
                value={selectedPromptId}
                onChange={(e) => setSelectedPromptId(e.target.value)}
                required
              >
                {experiments.find(e => e.id === selectedExpId)?.prompts?.map((p) => (
                  <option key={p.id} value={p.id}>
                    v{p.version} - {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Tuning Dataset</label>
              <select
                className="form-select"
                value={selectedDatasetId}
                onChange={(e) => setSelectedDatasetId(e.target.value)}
                required
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.train_count} tuning items)
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Optimization Objective</label>
              <select
                className="form-select"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              >
                <option value="maximize_accuracy">Maximize Accuracy</option>
                <option value="minimize_invalid_outputs">Zero Malformed / Invalid Labels</option>
                <option value="minimize_latency_with_threshold">Minimize Latency (Acc ≥ 80%)</option>
                <option value="balanced">Balanced Quality & Speed</option>
              </select>
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label">Max Iterations (Bound: 1-6)</label>
              <input
                type="number"
                min="1"
                max="6"
                className="form-input"
                value={maxIterations}
                onChange={(e) => setMaxIterations(e.target.value)}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={launching}
              style={{ minWidth: 180 }}
            >
              {launching ? (
                <>
                  <Activity size={16} className="spin" />
                  Optimizing...
                </>
              ) : (
                <>
                  <Play size={16} />
                  Start Optimizer Run
                </>
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Main Grid: Run History + Selected Run Deep Dive */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
        {/* Runs History */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Optimizer History ({runs.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 600, overflowY: 'auto' }}>
            {runs.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No optimizer runs yet. Launch your first run above.
              </div>
            ) : (
              runs.map((r) => {
                const isSelected = r.id === selectedRunId;
                const isDone = r.status === 'completed';
                return (
                  <div
                    key={r.id}
                    onClick={() => setSelectedRunId(r.id)}
                    style={{
                      padding: '12px 14px',
                      borderRadius: 8,
                      background: isSelected ? 'var(--primary-light)' : 'var(--bg-main)',
                      border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontWeight: 600, fontSize: '0.9rem', color: isSelected ? '#fff' : 'var(--text-primary)' }}>
                        {r.objective ? r.objective.replace('_', ' ') : 'Optimization'}
                      </span>
                      <span className={`badge ${isDone ? 'badge-success' : r.status === 'running' ? 'badge-info' : 'badge-warning'}`}>
                        {r.status}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span>{r.iterations_count || 0} iterations</span>
                      <span>•</span>
                      <span>{r.duration_seconds ? `${Math.round(r.duration_seconds)}s` : 'active'}</span>
                      <span>•</span>
                      <span style={{ fontFamily: 'var(--font-mono)' }}>{new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Run Details */}
        {selectedRun ? (
          <div>
            {/* Top Metric Cards */}
            <div className="grid-cards" style={{ marginBottom: 20 }}>
              <div className="metric-card">
                <div className="metric-header">
                  <span>Optimizer Status</span>
                  <Bot size={16} />
                </div>
                <div className="metric-value" style={{ textTransform: 'capitalize', fontSize: '1.4rem' }}>
                  {selectedRun.status}
                </div>
                <div className="metric-sub">
                  Reason: {selectedRun.convergence_reason || 'In progress'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Iterations Completed</span>
                  <Layers size={16} style={{ color: 'var(--primary)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--primary)' }}>
                  {selectedRun.iterations?.length || 0} / {selectedRun.max_iterations || 4}
                </div>
                <div className="metric-sub">
                  Objective: {selectedRun.objective}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Tools Invoked</span>
                  <Terminal size={16} style={{ color: 'var(--cyan)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--cyan)' }}>
                  {selectedRun.tool_logs?.length || 0}
                </div>
                <div className="metric-sub">Strictly typed audit log</div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Best Prompt Version</span>
                  <Sparkles size={16} style={{ color: 'var(--success)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--success)', fontSize: '1.4rem' }}>
                  {selectedRun.best_prompt_id ? 'Candidate Accepted' : 'Seed Baseline'}
                </div>
                <div className="metric-sub">Saved into Experiment</div>
              </div>
            </div>

            {/* Iteration Timeline */}
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title">
                <span>Iteration Timeline & Decisions</span>
                <span className="badge badge-info">{iterations.length} Cycles</span>
              </div>

              {iterations.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                  No iterations completed yet.
                </div>
              ) : (
                <div className="timeline">
                  {iterations.map((it, idx) => {
                    const isAccepted = it.decision === 'accepted';
                    const isExpanded = expandedStepId === it.id;
                    return (
                      <div key={it.id || idx} className="timeline-step">
                        <div
                          className="timeline-icon"
                          style={{
                            background: isAccepted ? 'var(--success-bg)' : 'var(--bg-card)',
                            color: isAccepted ? 'var(--success)' : 'var(--text-muted)',
                            border: `1px solid ${isAccepted ? 'var(--success)' : 'var(--border)'}`
                          }}
                        >
                          {isAccepted ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
                        </div>
                        <div className="timeline-content">
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <span className="timeline-title">
                                Iteration #{it.iteration_number}: Strategy - <code style={{ color: 'var(--cyan)', fontFamily: 'var(--font-mono)' }}>{it.strategy || 'hypothesis_mutation'}</code>
                              </span>
                              <span className={`badge ${isAccepted ? 'badge-success' : 'badge-danger'}`}>
                                {isAccepted ? 'Accepted (+Quality)' : 'Rejected'}
                              </span>
                            </div>
                            <button
                              className="btn btn-secondary btn-sm"
                              style={{ padding: '2px 8px', fontSize: '0.75rem' }}
                              onClick={() => setExpandedStepId(isExpanded ? null : it.id)}
                            >
                              {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              {isExpanded ? 'Hide Diff' : 'View Hypothesis & Diff'}
                            </button>
                          </div>

                          <div className="timeline-desc" style={{ marginBottom: 8 }}>
                            <strong>Hypothesis:</strong> {it.hypothesis || 'Targeted mutation based on observed failure cases.'}
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            <span>Baseline Score: <strong>{(it.baseline_score * 100).toFixed(1)}%</strong></span>
                            <span>•</span>
                            <span>Candidate Score: <strong>{(it.candidate_score * 100).toFixed(1)}%</strong></span>
                            <span>•</span>
                            <span style={{ color: (it.score_delta >= 0) ? 'var(--success)' : 'var(--danger)' }}>
                              Delta: {it.score_delta >= 0 ? '+' : ''}{(it.score_delta * 100).toFixed(1)}%
                            </span>
                          </div>

                          {isExpanded && (
                            <div style={{ marginTop: 12, borderTop: '1px solid var(--border)', paddingTop: 10 }}>
                              <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#fff', marginBottom: 4 }}>Mutated Prompt Instructions:</div>
                              <pre style={{ background: 'var(--bg-main)', padding: 10, borderRadius: 6, fontSize: '0.78rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', maxHeight: 160, overflowY: 'auto' }}>
                                {it.mutated_system_prompt || it.prompt_text || 'System prompt updated with edge case rules.'}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Tool Execution Logs Audit Drawer */}
            <div className="card">
              <div className="card-title">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Terminal size={18} style={{ color: 'var(--cyan)' }} />
                  <span>Strict Tool Execution Audit ({toolLogs.length} calls)</span>
                </div>
              </div>

              {toolLogs.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '16px 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                  No tool calls logged.
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 350, overflowY: 'auto' }}>
                  {toolLogs.map((log) => {
                    const isExpanded = expandedLogId === log.id;
                    return (
                      <div
                        key={log.id}
                        style={{
                          background: 'var(--bg-main)',
                          border: '1px solid var(--border)',
                          borderRadius: 6,
                          padding: '10px 14px'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <code style={{ color: 'var(--cyan)', fontWeight: 600, fontSize: '0.85rem' }}>
                              {log.tool_name}()
                            </code>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              Duration: {log.duration_ms ? `${Math.round(log.duration_ms)}ms` : '-'}
                            </span>
                          </div>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                            onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                          >
                            {isExpanded ? 'Hide Payload' : 'Inspect Input/Output'}
                          </button>
                        </div>

                        {isExpanded && (
                          <div style={{ marginTop: 10, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, borderTop: '1px solid var(--border)', paddingTop: 8 }}>
                            <div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Input Arguments:</div>
                              <pre style={{ background: 'var(--bg-card)', padding: 8, borderRadius: 4, fontSize: '0.75rem', maxHeight: 140, overflowY: 'auto' }}>
                                {typeof log.input_args === 'object' ? JSON.stringify(log.input_args, null, 2) : log.input_args}
                              </pre>
                            </div>
                            <div>
                              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 4 }}>Tool Output Result:</div>
                              <pre style={{ background: 'var(--bg-card)', padding: 8, borderRadius: 4, fontSize: '0.75rem', maxHeight: 140, overflowY: 'auto' }}>
                                {typeof log.output_result === 'object' ? JSON.stringify(log.output_result, null, 2) : log.output_result}
                              </pre>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 350 }}>
            <div className="empty-state">
              <Bot className="empty-state-icon" />
              <div className="empty-state-title">Select an optimizer run</div>
              <div className="empty-state-desc">Inspect step-by-step hypothesis, score progression, and tool audits.</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
