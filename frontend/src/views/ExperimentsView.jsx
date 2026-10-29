import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  Plus, 
  Trash2, 
  Download, 
  ExternalLink, 
  Sparkles, 
  Clock, 
  CheckCircle2, 
  Bot, 
  Calendar,
  AlertCircle
} from 'lucide-react';
import { api } from '../api/client';

export function ExperimentsView({ onNavigate }) {
  const [experiments, setExperiments] = useState([]);
  const [selectedExpId, setSelectedExpId] = useState('');
  const [selectedExp, setSelectedExp] = useState(null);
  const [loading, setLoading] = useState(true);

  // New Experiment Modal
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [taskType, setTaskType] = useState('sentiment_classification');
  const [objective, setObjective] = useState('maximize_accuracy');
  const [model, setModel] = useState('llama3.2:1b');
  const [creating, setCreating] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  useEffect(() => {
    loadExperiments();
  }, []);

  useEffect(() => {
    if (selectedExpId) {
      loadExperimentDetail(selectedExpId);
    }
  }, [selectedExpId]);

  async function loadExperiments() {
    setLoading(true);
    try {
      const data = await api.listExperiments();
      setExperiments(data);
      if (data.length > 0 && !selectedExpId) {
        setSelectedExpId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load experiments:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadExperimentDetail(id) {
    try {
      const exp = await api.getExperiment(id);
      setSelectedExp(exp);
    } catch (err) {
      console.error('Failed to load experiment detail:', err);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setErrorMsg(null);

    try {
      const newExp = await api.createExperiment({
        name,
        description,
        task_type: taskType,
        optimization_objective: objective,
        model,
      });

      await loadExperiments();
      setSelectedExpId(newExp.id);
      setModalOpen(false);
      setName('');
      setDescription('');
    } catch (err) {
      setErrorMsg(err.message || 'Failed to create experiment.');
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id, name) {
    if (!window.confirm(`Are you sure you want to delete experiment "${name}"? All associated prompts and evaluation logs will be permanently removed.`)) {
      return;
    }
    try {
      await api.deleteExperiment(id);
      const remaining = experiments.filter((e) => e.id !== id);
      setExperiments(remaining);
      if (remaining.length > 0) {
        setSelectedExpId(remaining[0].id);
      } else {
        setSelectedExp(null);
        setSelectedExpId('');
      }
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  }

  const prompts = selectedExp?.prompts || [];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Prompt Experiments</h1>
          <p className="page-subtitle">
            Manage projects, organize version trees, and track evolutionary histories across prompts.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-primary" onClick={() => setModalOpen(true)}>
            <Plus size={16} />
            New Experiment
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 24 }}>
        {/* Left List */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            All Experiments ({experiments.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {experiments.map((exp) => {
              const isSelected = exp.id === selectedExpId;
              return (
                <div
                  key={exp.id}
                  onClick={() => setSelectedExpId(exp.id)}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 8,
                    background: isSelected ? 'var(--primary-light)' : 'var(--bg-main)',
                    border: `1px solid ${isSelected ? 'var(--primary)' : 'var(--border)'}`,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '0.9rem', color: isSelected ? '#fff' : 'var(--text-primary)', marginBottom: 4 }}>
                    {exp.name}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>{exp.prompt_count || 0} prompt versions</span>
                    <span>•</span>
                    <span className="badge badge-neutral" style={{ fontSize: '0.65rem' }}>
                      {exp.task_type || 'classification'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Experiment Inspector */}
        {selectedExp ? (
          <div>
            {/* Header info bar */}
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16, marginBottom: 16 }}>
                <div>
                  <h2 style={{ fontSize: '1.35rem', fontWeight: 700, color: '#fff', marginBottom: 4 }}>
                    {selectedExp.name}
                  </h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                    {selectedExp.description || 'No description provided.'}
                  </p>
                </div>

                <div style={{ display: 'flex', gap: 10 }}>
                  <a
                    href={api.exportExperimentUrl(selectedExp.id)}
                    download
                    className="btn btn-secondary btn-sm"
                  >
                    <Download size={14} />
                    Export Archive (JSON)
                  </a>
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleDelete(selectedExp.id, selectedExp.name)}
                  >
                    <Trash2 size={14} />
                    Delete
                  </button>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 20, fontSize: '0.8rem', color: 'var(--text-muted)', borderTop: '1px solid var(--border)', paddingTop: 12 }}>
                <div>Task Type: <strong style={{ color: 'var(--text-primary)' }}>{selectedExp.task_type}</strong></div>
                <div>•</div>
                <div>Objective: <strong style={{ color: 'var(--text-primary)' }}>{selectedExp.optimization_objective}</strong></div>
                <div>•</div>
                <div>Default Model: <code style={{ color: 'var(--cyan)' }}>{selectedExp.model}</code></div>
                <div>•</div>
                <div>Created: <span style={{ color: 'var(--text-primary)' }}>{new Date(selectedExp.created_at).toLocaleDateString()}</span></div>
              </div>
            </div>

            {/* Prompt Versions Table / Tree */}
            <div className="card">
              <div className="card-title">
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Sparkles size={18} style={{ color: 'var(--primary)' }} />
                  <span>Prompt Version History ({prompts.length})</span>
                </div>
              </div>

              {prompts.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
                  No prompt versions recorded yet.
                </div>
              ) : (
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th style={{ width: 80 }}>Version</th>
                        <th>Name & Description</th>
                        <th style={{ width: 140 }}>Author</th>
                        <th style={{ width: 120 }}>Created</th>
                        <th style={{ width: 140 }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {prompts.map((p) => (
                        <tr key={p.id}>
                          <td>
                            <span className="badge badge-info" style={{ fontFamily: 'var(--font-mono)' }}>
                              v{p.version}
                            </span>
                          </td>
                          <td>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                              {p.name}
                            </div>
                            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2, fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 400 }}>
                              {p.system_prompt || p.user_template}
                            </div>
                          </td>
                          <td>
                            <span className={`badge ${p.author_type === 'agent' ? 'badge-warning' : 'badge-neutral'}`}>
                              {p.author_type === 'agent' ? '🤖 Agent Mutated' : '👤 User Manual'}
                            </span>
                          </td>
                          <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {new Date(p.created_at).toLocaleDateString()}
                          </td>
                          <td>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => {
                                if (onNavigate) {
                                  onNavigate('promptlab');
                                }
                              }}
                            >
                              <ExternalLink size={14} />
                              Open Lab
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 350 }}>
            <div className="empty-state">
              <Layers className="empty-state-icon" />
              <div className="empty-state-title">Select an experiment</div>
              <div className="empty-state-desc">Inspect version history, connected evaluations, and export JSON archives.</div>
            </div>
          </div>
        )}
      </div>

      {/* New Experiment Modal */}
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
          <div className="card" style={{ maxWidth: 500, width: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Plus size={20} style={{ color: 'var(--primary)' }} />
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#fff' }}>Create New Experiment</h2>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setModalOpen(false)}>✕</button>
            </div>

            {errorMsg && (
              <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.85rem' }}>
                {errorMsg}
              </div>
            )}

            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label className="form-label">Experiment Name *</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Sentiment Classification Benchmark"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  className="form-textarea"
                  style={{ minHeight: 70 }}
                  placeholder="Describe the target application and objectives..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Task Type</label>
                  <select
                    className="form-select"
                    value={taskType}
                    onChange={(e) => setTaskType(e.target.value)}
                  >
                    <option value="sentiment_classification">Sentiment Classification</option>
                    <option value="intent_detection">Intent Detection</option>
                    <option value="json_extraction">Structured JSON Extraction</option>
                    <option value="text_summarization">Summarization</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Default Model</label>
                  <input
                    type="text"
                    className="form-input"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Primary Optimization Objective</label>
                <select
                  className="form-select"
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                >
                  <option value="maximize_accuracy">Maximize Accuracy</option>
                  <option value="minimize_invalid_outputs">Zero Invalid Outputs</option>
                  <option value="minimize_latency_with_threshold">Minimize Latency with Threshold</option>
                  <option value="balanced">Balanced</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24 }}>
                <button type="button" className="btn btn-secondary" onClick={() => setModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Experiment'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
