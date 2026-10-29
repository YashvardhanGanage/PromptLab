import React, { useState, useEffect } from 'react';
import { 
  Play, 
  Save, 
  Copy, 
  Trash2, 
  Sparkles, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Bot,
  AlertCircle,
  Plus
} from 'lucide-react';
import { api } from '../api/client';

export function PromptLabView({ onNavigate }) {
  const [experiments, setExperiments] = useState([]);
  const [selectedExpId, setSelectedExpId] = useState('');
  const [currentExp, setCurrentExp] = useState(null);
  const [selectedPromptId, setSelectedPromptId] = useState('');

  // Prompt edit state
  const [promptName, setPromptName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [userTemplate, setUserTemplate] = useState('');
  const [validLabels, setValidLabels] = useState('positive, negative, neutral');
  const [outputFormat, setOutputFormat] = useState('labels');

  // Single test playground
  const [testInput, setTestInput] = useState('The food was surprisingly not bad at all despite the awful reviews.');
  const [testExpected, setTestExpected] = useState('positive');
  const [singleResult, setSingleResult] = useState(null);
  const [testingSingle, setTestingSingle] = useState(false);

  // Status & saving
  const [saving, setSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  // Load experiments on mount
  useEffect(() => {
    loadExperiments();
  }, []);

  async function loadExperiments() {
    try {
      const data = await api.listExperiments();
      setExperiments(data);
      if (data.length > 0 && !selectedExpId) {
        selectExperiment(data[0].id);
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function selectExperiment(expId) {
    setSelectedExpId(expId);
    try {
      const exp = await api.getExperiment(expId);
      setCurrentExp(exp);
      if (exp.prompts && exp.prompts.length > 0) {
        const bestOrFirst = exp.best_prompt || exp.prompts[0];
        loadPromptData(bestOrFirst);
      }
    } catch (err) {
      console.error(err);
    }
  }

  function loadPromptData(p) {
    setSelectedPromptId(p.id);
    setPromptName(p.name);
    setSystemPrompt(p.system_prompt);
    setUserTemplate(p.user_template);
    setOutputFormat(p.output_format || 'labels');
    setValidLabels((p.valid_labels || []).join(', '));
  }

  async function handleSavePrompt() {
    if (!selectedPromptId) return;
    setSaving(true);
    setStatusMsg(null);
    try {
      const labelsArray = validLabels.split(',').map(s => s.trim()).filter(Boolean);
      await api.updatePrompt(selectedPromptId, {
        name: promptName,
        system_prompt: systemPrompt,
        user_template: userTemplate,
        output_format: outputFormat,
        valid_labels: labelsArray
      });
      setStatusMsg({ type: 'success', text: 'Prompt updated successfully!' });
      selectExperiment(selectedExpId);
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  }

  async function handleDuplicatePrompt() {
    if (!currentExp) return;
    try {
      const labelsArray = validLabels.split(',').map(s => s.trim()).filter(Boolean);
      const newPrompt = await api.createPrompt({
        experiment_id: selectedExpId,
        name: `${promptName} (Copy)`,
        system_prompt: systemPrompt,
        user_template: userTemplate,
        output_format: outputFormat,
        valid_labels: labelsArray
      });
      setStatusMsg({ type: 'success', text: 'Prompt cloned into new version!' });
      await selectExperiment(selectedExpId);
      loadPromptData(newPrompt);
    } catch (err) {
      setStatusMsg({ type: 'error', text: err.message });
    }
  }

  async function handleRunSingle() {
    setTestingSingle(true);
    setSingleResult(null);
    try {
      const labelsArray = validLabels.split(',').map(s => s.trim()).filter(Boolean);
      const res = await api.runSinglePrompt({
        system_prompt: systemPrompt,
        user_template: userTemplate,
        input_text: testInput,
        expected_output: testExpected,
        output_format: outputFormat,
        valid_labels: labelsArray
      });
      setSingleResult(res);
    } catch (err) {
      setSingleResult({ error_message: err.message });
    } finally {
      setTestingSingle(false);
    }
  }

  async function handleCreateNewExperiment() {
    const name = prompt('Enter a name for the new experiment:');
    if (!name) return;
    try {
      const created = await api.createExperiment({
        name,
        description: 'Custom prompt experiment',
        task_type: 'classification',
        objective: 'maximize_accuracy'
      });
      await loadExperiments();
      selectExperiment(created.id);
    } catch (err) {
      alert(`Error creating experiment: ${err.message}`);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Prompt Lab Workspace</h1>
          <p className="page-subtitle">Iterate, inspect outputs, and benchmark prompt candidates with deterministic evidence.</p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={handleCreateNewExperiment}>
            <Plus size={16} /> New Experiment
          </button>
          <button className="btn btn-primary" onClick={() => onNavigate('agent')}>
            <Bot size={16} /> Run Agentic Optimizer
          </button>
        </div>
      </div>

      {/* Experiment Selector Bar */}
      <div className="card" style={{ padding: '16px 20px', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 220 }}>
            <label className="form-label">Active Experiment</label>
            <select 
              className="form-select"
              value={selectedExpId}
              onChange={(e) => selectExperiment(e.target.value)}
            >
              {experiments.map(exp => (
                <option key={exp.id} value={exp.id}>{exp.name}</option>
              ))}
            </select>
          </div>

          {currentExp?.prompts && currentExp.prompts.length > 0 && (
            <div style={{ minWidth: 220 }}>
              <label className="form-label">Prompt Version</label>
              <select 
                className="form-select"
                value={selectedPromptId}
                onChange={(e) => {
                  const p = currentExp.prompts.find(item => item.id === e.target.value);
                  if (p) loadPromptData(p);
                }}
              >
                {currentExp.prompts.map(p => (
                  <option key={p.id} value={p.id}>
                    v{p.version_num}: {p.name} {p.is_best ? '★ (Best)' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, alignSelf: 'flex-end' }}>
            <button className="btn btn-secondary btn-sm" onClick={handleDuplicatePrompt}>
              <Copy size={14} /> Duplicate
            </button>
            <button className="btn btn-primary btn-sm" onClick={handleSavePrompt} disabled={saving}>
              <Save size={14} /> {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {statusMsg && (
          <div style={{ marginTop: 12, fontSize: '0.85rem', color: statusMsg.type === 'success' ? 'var(--success)' : 'var(--danger)' }}>
            {statusMsg.text}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 24 }}>
        {/* Left Column: Prompt Template Editor */}
        <div className="card">
          <div className="card-title">Prompt Definition</div>

          <div className="form-group">
            <label className="form-label">Prompt Version Name</label>
            <input 
              type="text" 
              className="form-input" 
              value={promptName} 
              onChange={(e) => setPromptName(e.target.value)} 
            />
          </div>

          <div className="form-group">
            <label className="form-label">System Instructions</label>
            <textarea 
              className="form-textarea" 
              style={{ minHeight: 140 }}
              value={systemPrompt}
              onChange={(e) => setSystemPrompt(e.target.value)}
              placeholder="e.g. You are a precise sentiment classifier. Output strictly one of: positive, negative, neutral."
            />
          </div>

          <div className="form-group">
            <label className="form-label">User Template (Include <code>{'{input}'}</code>)</label>
            <textarea 
              className="form-textarea" 
              style={{ minHeight: 100 }}
              value={userTemplate}
              onChange={(e) => setUserTemplate(e.target.value)}
              placeholder="Text: {input}\nClassification:"
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Output Format</label>
              <select 
                className="form-select"
                value={outputFormat}
                onChange={(e) => setOutputFormat(e.target.value)}
              >
                <option value="labels">Exact Label Set</option>
                <option value="json">Structured JSON</option>
                <option value="free_text">Free Text</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Allowed Output Labels</label>
              <input 
                type="text" 
                className="form-input" 
                value={validLabels}
                onChange={(e) => setValidLabels(e.target.value)}
                placeholder="positive, negative, neutral"
              />
            </div>
          </div>
        </div>

        {/* Right Column: Interactive Single-Run Playground */}
        <div className="card">
          <div className="card-title">Live Example Playground</div>
          
          <div className="form-group">
            <label className="form-label">Input Text to Test</label>
            <textarea 
              className="form-textarea"
              style={{ minHeight: 80 }}
              value={testInput}
              onChange={(e) => setTestInput(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Expected Output (Optional verification)</label>
            <input 
              type="text" 
              className="form-input"
              value={testExpected}
              onChange={(e) => setTestExpected(e.target.value)}
            />
          </div>

          <button 
            className="btn btn-primary" 
            style={{ width: '100%', marginBottom: 18 }}
            onClick={handleRunSingle}
            disabled={testingSingle || !testInput.trim()}
          >
            <Play size={16} /> {testingSingle ? 'Running Model...' : 'Test Prompt Live'}
          </button>

          {/* Test Execution Output */}
          {singleResult && (
            <div style={{ background: 'var(--bg-main)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>EXECUTION RESULT</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--cyan)' }}>
                  <Clock size={12} style={{ display: 'inline', marginRight: 4 }} />
                  {singleResult.latency_ms?.toFixed(1)} ms
                </span>
              </div>

              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Raw Model Output:</div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: '#fff', marginTop: 2 }}>
                  {singleResult.raw_output || '<empty>'}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 12 }}>
                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Parsed Label:</span>
                  <span className="badge badge-info" style={{ marginTop: 2 }}>{singleResult.parsed_output || 'None'}</span>
                </div>

                <div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Format Valid:</span>
                  <span className={`badge ${singleResult.is_valid ? 'badge-success' : 'badge-danger'}`} style={{ marginTop: 2 }}>
                    {singleResult.is_valid ? 'Valid' : singleResult.error_message || 'Invalid'}
                  </span>
                </div>

                {singleResult.is_correct !== null && (
                  <div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Correctness:</span>
                    <span className={`badge ${singleResult.is_correct ? 'badge-success' : 'badge-danger'}`} style={{ marginTop: 2 }}>
                      {singleResult.is_correct ? 'Match' : 'Mismatch'}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
