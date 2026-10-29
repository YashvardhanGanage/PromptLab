import React, { useState, useEffect } from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Clock, 
  Play, 
  Download, 
  GitCompare, 
  Layers, 
  FileText, 
  Filter,
  BarChart3,
  Sparkles,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Info
} from 'lucide-react';
import { api } from '../api/client';

export function EvaluationsView() {
  const [evaluations, setEvaluations] = useState([]);
  const [selectedEvalId, setSelectedEvalId] = useState('');
  const [selectedEval, setSelectedEval] = useState(null);
  const [failureAnalysis, setFailureAnalysis] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');

  // New Eval Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [experiments, setExperiments] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [selectedExpId, setSelectedExpId] = useState('');
  const [selectedPromptId, setSelectedPromptId] = useState('');
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [selectedSplit, setSelectedSplit] = useState('all');
  const [runningEval, setRunningEval] = useState(false);
  const [runError, setRunError] = useState(null);

  // Comparison State
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [baselineEvalId, setBaselineEvalId] = useState('');
  const [candidateEvalId, setCandidateEvalId] = useState('');
  const [compareObjective, setCompareObjective] = useState('maximize_accuracy');
  const [comparisonResult, setComparisonResult] = useState(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    loadEvaluations();
    loadSetupData();
  }, []);

  useEffect(() => {
    if (selectedEvalId) {
      loadEvaluationDetail(selectedEvalId);
    }
  }, [selectedEvalId]);

  async function loadEvaluations() {
    setLoading(true);
    try {
      const data = await api.listEvaluations();
      setEvaluations(data);
      if (data.length > 0 && !selectedEvalId) {
        setSelectedEvalId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load evaluations:', err);
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
          setSelectedPromptId(exp.prompts[exp.prompts.length - 1].id);
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
        setSelectedPromptId(exp.prompts[exp.prompts.length - 1].id);
      } else {
        setSelectedPromptId('');
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function loadEvaluationDetail(id) {
    try {
      const ev = await api.getEvaluation(id);
      setSelectedEval(ev);
      try {
        const fa = await api.getFailureAnalysis(id);
        setFailureAnalysis(fa);
      } catch (e) {
        setFailureAnalysis(null);
      }
    } catch (err) {
      console.error('Failed to load evaluation details:', err);
    }
  }

  async function handleRunEvaluation(e) {
    e.preventDefault();
    if (!selectedPromptId || !selectedDatasetId) {
      setRunError('Please select both a prompt and a dataset.');
      return;
    }
    setRunningEval(true);
    setRunError(null);

    try {
      const res = await api.createEvaluation({
        prompt_id: selectedPromptId,
        dataset_id: selectedDatasetId,
        split: selectedSplit,
      });
      await loadEvaluations();
      setSelectedEvalId(res.id);
      setModalOpen(false);
    } catch (err) {
      setRunError(err.message || 'Evaluation failed.');
    } finally {
      setRunningEval(false);
    }
  }

  async function handleCompare(e) {
    e.preventDefault();
    if (!baselineEvalId || !candidateEvalId) return;
    setComparing(true);
    try {
      const result = await api.compareEvaluations(baselineEvalId, candidateEvalId, compareObjective);
      setComparisonResult(result);
    } catch (err) {
      console.error('Comparison error:', err);
    } finally {
      setComparing(false);
    }
  }

  const results = selectedEval?.results || [];
  const filteredResults = results.filter((r) => {
    if (statusFilter === 'all') return true;
    if (statusFilter === 'correct') return r.is_correct && !r.is_invalid;
    if (statusFilter === 'incorrect') return !r.is_correct && !r.is_invalid;
    if (statusFilter === 'invalid') return r.is_invalid;
    return true;
  });

  const cmData = selectedEval?.confusion_matrix || null;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Prompt Evaluations</h1>
          <p className="page-subtitle">
            Systematic benchmark evaluations, Scikit-learn confusion matrices, and failure diagnostics.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={() => setCompareModalOpen(true)}>
            <GitCompare size={16} />
            Compare Prompts
          </button>
          <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
            <Play size={16} />
            New Evaluation
          </button>
        </div>
      </div>

      {/* Main Grid: Left selector, Right inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24, marginBottom: 24 }}>
        {/* Evaluations History List */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Evaluation History ({evaluations.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: '600px', overflowY: 'auto' }}>
            {evaluations.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '24px 8px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                No evaluations recorded yet. Run your first benchmark above.
              </div>
            ) : (
              evaluations.map((ev) => {
                const isSelected = ev.id === selectedEvalId;
                const acc = Math.round((ev.accuracy || 0) * 100);
                return (
                  <div
                    key={ev.id}
                    onClick={() => setSelectedEvalId(ev.id)}
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
                        {ev.prompt_name || 'Prompt v1'}
                      </span>
                      <span className={`badge ${acc >= 80 ? 'badge-success' : acc >= 60 ? 'badge-warning' : 'badge-danger'}`}>
                        {acc}% Acc
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      <span>{ev.dataset_name || 'Benchmark'}</span>
                      <span>•</span>
                      <span style={{ textTransform: 'uppercase' }}>{ev.split || 'all'}</span>
                      <span>•</span>
                      <span>{Math.round(ev.latency_avg_ms || 0)}ms</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Evaluation Inspector */}
        {selectedEval ? (
          <div>
            {/* Top Stat Cards */}
            <div className="grid-cards" style={{ marginBottom: 20 }}>
              <div className="metric-card">
                <div className="metric-header">
                  <span>Accuracy</span>
                  <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--success)' }}>
                  {Math.round((selectedEval.accuracy || 0) * 100)}%
                </div>
                <div className="metric-sub">
                  {selectedEval.correct_predictions} / {selectedEval.total_examples} correct
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Macro F1</span>
                  <BarChart3 size={16} style={{ color: 'var(--cyan)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--cyan)' }}>
                  {selectedEval.macro_f1 != null ? (selectedEval.macro_f1 * 100).toFixed(1) + '%' : 'N/A'}
                </div>
                <div className="metric-sub">
                  P: {selectedEval.macro_precision != null ? (selectedEval.macro_precision * 100).toFixed(0) + '%' : '-'} | R: {selectedEval.macro_recall != null ? (selectedEval.macro_recall * 100).toFixed(0) + '%' : '-'}
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Avg Latency</span>
                  <Clock size={16} />
                </div>
                <div className="metric-value">
                  {Math.round(selectedEval.latency_avg_ms || 0)}ms
                </div>
                <div className="metric-sub">
                  P95: {Math.round(selectedEval.latency_p95_ms || 0)}ms
                </div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Invalid Outputs</span>
                  <AlertTriangle size={16} style={{ color: selectedEval.invalid_outputs > 0 ? 'var(--danger)' : 'var(--text-muted)' }} />
                </div>
                <div className="metric-value" style={{ color: selectedEval.invalid_outputs > 0 ? 'var(--danger)' : 'var(--text-primary)' }}>
                  {selectedEval.invalid_outputs || 0}
                </div>
                <div className="metric-sub">
                  Error rate: {Math.round((selectedEval.error_rate || 0) * 100)}%
                </div>
              </div>
            </div>

            {/* Export & Details Bar */}
            <div className="card" style={{ padding: '14px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <div>
                <span style={{ fontWeight: 600, color: '#fff' }}>{selectedEval.prompt_name}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 12 }}>
                  Model: <code style={{ color: 'var(--cyan)', fontFamily: 'var(--font-mono)' }}>{selectedEval.model || 'llama3.2:1b'}</code>
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginLeft: 12 }}>
                  Split: <span className="badge badge-info" style={{ textTransform: 'uppercase' }}>{selectedEval.split || 'all'}</span>
                </span>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <a
                  href={api.exportEvaluationUrl(selectedEval.id, 'csv')}
                  download
                  className="btn btn-secondary btn-sm"
                >
                  <Download size={14} />
                  CSV
                </a>
                <a
                  href={api.exportEvaluationUrl(selectedEval.id, 'json')}
                  download
                  className="btn btn-secondary btn-sm"
                >
                  <Download size={14} />
                  JSON
                </a>
              </div>
            </div>

            {/* Confusion Matrix & Failure Breakdown Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: cmData ? '1fr 1fr' : '1fr', gap: 20, marginBottom: 20 }}>
              {/* Confusion Matrix */}
              {cmData && cmData.classes && cmData.classes.length > 0 && (
                <div className="card">
                  <div className="card-title">
                    <span>Confusion Matrix</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 400 }}>
                      Rows: Ground Truth • Cols: Predicted
                    </span>
                  </div>

                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ textAlign: 'center', borderCollapse: 'separate', borderSpacing: 4 }}>
                      <thead>
                        <tr>
                          <th style={{ background: 'transparent', textAlign: 'left', fontSize: '0.75rem' }}>Actual \ Pred</th>
                          {cmData.classes.map((cls) => (
                            <th key={cls} style={{ textTransform: 'capitalize', fontSize: '0.75rem', padding: '6px 10px' }}>
                              {cls}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {cmData.classes.map((actualCls, rowIdx) => (
                          <tr key={actualCls}>
                            <td style={{ textAlign: 'left', fontWeight: 600, textTransform: 'capitalize', fontSize: '0.8rem', padding: '8px 10px' }}>
                              {actualCls}
                            </td>
                            {cmData.classes.map((predCls, colIdx) => {
                              const count = cmData.matrix[rowIdx] ? cmData.matrix[rowIdx][colIdx] : 0;
                              const isDiagonal = rowIdx === colIdx;
                              return (
                                <td
                                  key={predCls}
                                  style={{
                                    padding: '10px',
                                    borderRadius: 6,
                                    background: isDiagonal
                                      ? count > 0 ? 'rgba(16, 185, 129, 0.25)' : 'var(--bg-surface)'
                                      : count > 0 ? 'rgba(239, 68, 68, 0.25)' : 'var(--bg-main)',
                                    color: count > 0 ? '#fff' : 'var(--text-muted)',
                                    fontWeight: 700,
                                    fontSize: '0.9rem',
                                    border: isDiagonal && count > 0 ? '1px solid rgba(16, 185, 129, 0.5)' : '1px solid var(--border)'
                                  }}
                                >
                                  {count}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Failure Analysis / Diagnostics */}
              <div className="card">
                <div className="card-title">
                  <span>Failure Diagnostics</span>
                  <span className="badge badge-warning">
                    {failureAnalysis ? failureAnalysis.total_failures : 0} Failures
                  </span>
                </div>

                {failureAnalysis && failureAnalysis.total_failures > 0 ? (
                  <div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
                      {Object.entries(failureAnalysis.category_breakdown || {}).map(([cat, count]) => (
                        <div key={cat} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-main)', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border)' }}>
                          <span style={{ fontSize: '0.85rem', textTransform: 'capitalize', color: 'var(--text-primary)' }}>
                            {cat.replace('_', ' ')}
                          </span>
                          <span className="badge badge-danger">{count}</span>
                        </div>
                      ))}
                    </div>

                    {failureAnalysis.recommendation && (
                      <div style={{ background: 'var(--bg-surface)', padding: 12, borderRadius: 8, border: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--warning)', fontSize: '0.8rem', fontWeight: 600, marginBottom: 4 }}>
                          <Sparkles size={14} /> Recommended Prompt Strategy
                        </div>
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                          {failureAnalysis.recommendation}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--success)' }}>
                    <CheckCircle2 size={36} style={{ margin: '0 auto 10px', opacity: 0.8 }} />
                    <div style={{ fontWeight: 600 }}>Zero Failures Recorded</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      All evaluated examples yielded correct, valid labels.
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Example Results Table */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ fontWeight: 600, color: '#fff', fontSize: '1rem' }}>Evaluated Examples</span>
                  <span className="badge badge-neutral">{filteredResults.length} of {results.length}</span>
                </div>

                <div style={{ display: 'flex', background: 'var(--bg-main)', padding: 3, borderRadius: 8, border: '1px solid var(--border)' }}>
                  <button
                    className={`btn btn-sm ${statusFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ border: 'none', borderRadius: 6 }}
                    onClick={() => setStatusFilter('all')}
                  >
                    All ({results.length})
                  </button>
                  <button
                    className={`btn btn-sm ${statusFilter === 'incorrect' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ border: 'none', borderRadius: 6 }}
                    onClick={() => setStatusFilter('incorrect')}
                  >
                    Incorrect ({results.filter(r => !r.is_correct && !r.is_invalid).length})
                  </button>
                  <button
                    className={`btn btn-sm ${statusFilter === 'invalid' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ border: 'none', borderRadius: 6 }}
                    onClick={() => setStatusFilter('invalid')}
                  >
                    Invalid ({results.filter(r => r.is_invalid).length})
                  </button>
                  <button
                    className={`btn btn-sm ${statusFilter === 'correct' ? 'btn-primary' : 'btn-secondary'}`}
                    style={{ border: 'none', borderRadius: 6 }}
                    onClick={() => setStatusFilter('correct')}
                  >
                    Correct ({results.filter(r => r.is_correct && !r.is_invalid).length})
                  </button>
                </div>
              </div>

              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th style={{ width: 85 }}>Status</th>
                      <th>Input Text</th>
                      <th style={{ width: 110 }}>Expected</th>
                      <th style={{ width: 110 }}>Predicted</th>
                      <th style={{ width: 85 }}>Latency</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredResults.map((r) => (
                      <tr key={r.id}>
                        <td>
                          {r.is_invalid ? (
                            <span className="badge badge-danger">Invalid</span>
                          ) : r.is_correct ? (
                            <span className="badge badge-success">Correct</span>
                          ) : (
                            <span className="badge badge-warning">Failed</span>
                          )}
                        </td>
                        <td style={{ color: 'var(--text-primary)', lineHeight: 1.4 }}>
                          {r.input_text}
                        </td>
                        <td>
                          <span className="badge badge-neutral">{r.expected_output}</span>
                        </td>
                        <td>
                          <span className={`badge ${r.is_correct ? 'badge-success' : 'badge-danger'}`}>
                            {r.actual_output || '<empty>'}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
                          {Math.round(r.latency_ms)}ms
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 350 }}>
            <div className="empty-state">
              <BarChart3 className="empty-state-icon" />
              <div className="empty-state-title">Select an evaluation</div>
              <div className="empty-state-desc">Choose a run from the history list to inspect metrics, matrix, and failure cases.</div>
            </div>
          </div>
        )}
      </div>

      {/* New Evaluation Modal */}
      {modalOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: 20
        }}>
          <div className="card" style={{ maxWidth: 520, width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Play size={20} style={{ color: 'var(--primary)' }} />
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#fff' }}>Run Benchmark Evaluation</h2>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setModalOpen(false)}>✕</button>
            </div>

            {runError && (
              <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.85rem' }}>
                {runError}
              </div>
            )}

            <form onSubmit={handleRunEvaluation}>
              <div className="form-group">
                <label className="form-label">Select Experiment</label>
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

              <div className="form-group">
                <label className="form-label">Prompt Version</label>
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

              <div className="form-group">
                <label className="form-label">Benchmark Dataset</label>
                <select
                  className="form-select"
                  value={selectedDatasetId}
                  onChange={(e) => setSelectedDatasetId(e.target.value)}
                  required
                >
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name} ({d.total_examples} examples)
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Evaluation Split</label>
                <select
                  className="form-select"
                  value={selectedSplit}
                  onChange={(e) => setSelectedSplit(e.target.value)}
                >
                  <option value="all">Full Dataset (Tuning + Held-Out)</option>
                  <option value="train">Tuning Split Only (for Prompt Optimization)</option>
                  <option value="test">Held-Out Split Only (Unbiased Test)</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={runningEval}>
                  {runningEval ? 'Evaluating...' : 'Start Evaluation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Compare Prompts Modal */}
      {compareModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 100,
          padding: 20
        }}>
          <div className="card" style={{ maxWidth: 700, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <GitCompare size={20} style={{ color: 'var(--primary)' }} />
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#fff' }}>Pairwise Candidate Comparison</h2>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => { setCompareModalOpen(false); setComparisonResult(null); }}>✕</button>
            </div>

            <form onSubmit={handleCompare} style={{ marginBottom: 20 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Baseline Evaluation</label>
                  <select
                    className="form-select"
                    value={baselineEvalId}
                    onChange={(e) => setBaselineEvalId(e.target.value)}
                    required
                  >
                    <option value="">Select Baseline...</option>
                    {evaluations.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.prompt_name} ({Math.round((ev.accuracy || 0) * 100)}% Acc)
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Candidate Evaluation</label>
                  <select
                    className="form-select"
                    value={candidateEvalId}
                    onChange={(e) => setCandidateEvalId(e.target.value)}
                    required
                  >
                    <option value="">Select Candidate...</option>
                    {evaluations.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.prompt_name} ({Math.round((ev.accuracy || 0) * 100)}% Acc)
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Optimization Objective</label>
                <select
                  className="form-select"
                  value={compareObjective}
                  onChange={(e) => setCompareObjective(e.target.value)}
                >
                  <option value="maximize_accuracy">Maximize Accuracy</option>
                  <option value="minimize_invalid_outputs">Minimize Invalid Outputs</option>
                  <option value="minimize_latency_with_threshold">Minimize Latency with Acc Threshold</option>
                  <option value="balanced">Balanced (Acc + Latency Tradeoff)</option>
                </select>
              </div>

              <button
                type="submit"
                className="btn btn-primary"
                style={{ width: '100%' }}
                disabled={comparing || !baselineEvalId || !candidateEvalId}
              >
                {comparing ? 'Calculating Deltas...' : 'Run Pairwise Comparison'}
              </button>
            </form>

            {comparisonResult && (
              <div style={{ marginTop: 24, borderTop: '1px solid var(--border)', paddingTop: 20 }}>
                {/* Decision Badge */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: comparisonResult.verdict === 'accepted' ? 'var(--success-bg)' : 'var(--danger-bg)', padding: '12px 16px', borderRadius: 8, marginBottom: 16 }}>
                  <div>
                    <span style={{ fontWeight: 700, fontSize: '1rem', color: comparisonResult.verdict === 'accepted' ? 'var(--success)' : 'var(--danger)' }}>
                      Decision: {comparisonResult.verdict === 'accepted' ? 'Candidate Accepted' : 'Candidate Rejected'}
                    </span>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                      {comparisonResult.reason}
                    </div>
                  </div>
                </div>

                {/* Delta Stats */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
                  <div style={{ background: 'var(--bg-main)', padding: 12, borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Accuracy Delta</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: (comparisonResult.accuracy_delta || 0) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                      {(comparisonResult.accuracy_delta || 0) >= 0 ? '+' : ''}{((comparisonResult.accuracy_delta || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div style={{ background: 'var(--bg-main)', padding: 12, borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Latency Delta</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: (comparisonResult.latency_delta_ms || 0) <= 0 ? 'var(--success)' : 'var(--warning)' }}>
                      {(comparisonResult.latency_delta_ms || 0) <= 0 ? '' : '+'}{Math.round(comparisonResult.latency_delta_ms || 0)}ms
                    </div>
                  </div>
                  <div style={{ background: 'var(--bg-main)', padding: 12, borderRadius: 8, textAlign: 'center', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Invalid Delta</div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: (comparisonResult.invalid_delta || 0) <= 0 ? 'var(--success)' : 'var(--danger)' }}>
                      {(comparisonResult.invalid_delta || 0) <= 0 ? '' : '+'}{comparisonResult.invalid_delta || 0}
                    </div>
                  </div>
                </div>

                {/* Regressed and Improved Lists */}
                {comparisonResult.regressed_examples && comparisonResult.regressed_examples.length > 0 && (
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ color: 'var(--danger)', fontWeight: 600, fontSize: '0.85rem', marginBottom: 6 }}>
                      ⚠️ Regressed Examples ({comparisonResult.regressed_examples.length}) - Worked before, broke now:
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {comparisonResult.regressed_examples.slice(0, 3).map((r, i) => (
                        <div key={i} style={{ background: 'var(--bg-surface)', padding: '8px 12px', borderRadius: 6, fontSize: '0.8rem' }}>
                          <div>{r.input_text}</div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 2 }}>
                            Expected: <code style={{ color: 'var(--success)' }}>{r.expected}</code> | Baseline: <code style={{ color: 'var(--success)' }}>{r.baseline_output}</code> | Candidate: <code style={{ color: 'var(--danger)' }}>{r.candidate_output}</code>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {comparisonResult.improved_examples && comparisonResult.improved_examples.length > 0 && (
                  <div>
                    <div style={{ color: 'var(--success)', fontWeight: 600, fontSize: '0.85rem', marginBottom: 6 }}>
                      ✨ Improved Examples ({comparisonResult.improved_examples.length}) - Failed before, now fixed:
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {comparisonResult.improved_examples.slice(0, 3).map((imp, i) => (
                        <div key={i} style={{ background: 'var(--bg-surface)', padding: '8px 12px', borderRadius: 6, fontSize: '0.8rem' }}>
                          <div>{imp.input_text}</div>
                          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: 2 }}>
                            Expected: <code style={{ color: 'var(--success)' }}>{imp.expected}</code> | Candidate Fixed: <code style={{ color: 'var(--success)' }}>{imp.candidate_output}</code>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
