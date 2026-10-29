import React, { useState, useEffect } from 'react';
import { 
  Database, 
  Upload, 
  FileText, 
  Filter, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles,
  Layers,
  Search,
  Hash,
  Split,
  ChevronRight
} from 'lucide-react';
import { api } from '../api/client';

export function DatasetsView() {
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState('');
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [examples, setExamples] = useState([]);
  const [splitFilter, setSplitFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);

  // Upload form state
  const [uploadName, setUploadName] = useState('');
  const [uploadDesc, setUploadDesc] = useState('');
  const [uploadFile, setUploadFile] = useState(null);
  const [inputCol, setInputCol] = useState('input');
  const [outputCol, setOutputCol] = useState('expected_output');
  const [splitRatio, setSplitRatio] = useState(0.70);

  useEffect(() => {
    loadDatasets();
  }, []);

  useEffect(() => {
    if (selectedDatasetId) {
      loadDatasetDetails(selectedDatasetId, splitFilter);
    }
  }, [selectedDatasetId, splitFilter]);

  async function loadDatasets() {
    setLoading(true);
    try {
      const data = await api.listDatasets();
      setDatasets(data);
      if (data.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load datasets:', err);
    } finally {
      setLoading(false);
    }
  }

  async function loadDatasetDetails(id, split = '') {
    try {
      const ds = await api.getDataset(id);
      setSelectedDataset(ds);
      const exData = await api.getDatasetExamples(id, split, 100);
      setExamples(exData.examples || []);
    } catch (err) {
      console.error('Failed to load dataset details:', err);
    }
  }

  async function handleFileUpload(e) {
    e.preventDefault();
    if (!uploadFile) {
      setUploadError('Please select a CSV or JSON file to upload.');
      return;
    }
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    formData.append('file', uploadFile);
    formData.append('name', uploadName || uploadFile.name.replace(/\.[^/.]+$/, ''));
    formData.append('description', uploadDesc);
    formData.append('input_column', inputCol);
    formData.append('output_column', outputCol);
    formData.append('train_split_ratio', splitRatio);

    try {
      const res = await api.uploadDataset(formData);
      setUploadSuccess(`Successfully uploaded "${res.name}" with ${res.total_examples} examples (${res.train_count} tuning, ${res.test_count} held-out).`);
      await loadDatasets();
      setSelectedDatasetId(res.id);
      setTimeout(() => {
        setUploadModalOpen(false);
        setUploadSuccess(null);
        setUploadFile(null);
        setUploadName('');
        setUploadDesc('');
      }, 1500);
    } catch (err) {
      setUploadError(err.message || 'Dataset upload failed.');
    } finally {
      setUploading(false);
    }
  }

  const filteredExamples = examples.filter((ex) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      ex.input_text.toLowerCase().includes(term) ||
      ex.expected_output.toLowerCase().includes(term) ||
      (ex.category_tag && ex.category_tag.toLowerCase().includes(term))
    );
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dataset Management</h1>
          <p className="page-subtitle">
            Upload, partition, and inspect benchmark datasets for prompt evaluation and tuning.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-primary" onClick={() => setUploadModalOpen(true)}>
            <Upload size={16} />
            Upload Dataset
          </button>
        </div>
      </div>

      {uploadSuccess && (
        <div style={{ background: 'var(--success-bg)', border: '1px solid var(--success)', color: 'var(--success)', padding: '12px 16px', borderRadius: 8, marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
          <CheckCircle2 size={18} />
          <span>{uploadSuccess}</span>
        </div>
      )}

      {/* Dataset Selector & Info Bar */}
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 24, marginBottom: 24 }}>
        {/* Dataset list card */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Available Datasets ({datasets.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {datasets.map((ds) => {
              const isSelected = ds.id === selectedDatasetId;
              return (
                <div
                  key={ds.id}
                  onClick={() => setSelectedDatasetId(ds.id)}
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
                    {ds.name}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    <span>{ds.total_examples} examples</span>
                    <span>•</span>
                    <span className="badge badge-info" style={{ fontSize: '0.65rem', padding: '1px 5px' }}>{ds.task_type || 'sentiment'}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected Dataset Details & Partition Overview */}
        {selectedDataset && (
          <div>
            <div className="grid-cards" style={{ marginBottom: 20 }}>
              <div className="metric-card">
                <div className="metric-header">
                  <span>Total Examples</span>
                  <Database size={16} />
                </div>
                <div className="metric-value">{selectedDataset.total_examples}</div>
                <div className="metric-sub">Deduplicated & validated</div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Tuning Partition</span>
                  <Split size={16} style={{ color: 'var(--primary)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--primary)' }}>
                  {selectedDataset.train_count}
                </div>
                <div className="metric-sub">For iterative optimization</div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Held-Out Partition</span>
                  <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />
                </div>
                <div className="metric-value" style={{ color: 'var(--success)' }}>
                  {selectedDataset.test_count}
                </div>
                <div className="metric-sub">Strictly isolated evaluation</div>
              </div>

              <div className="metric-card">
                <div className="metric-header">
                  <span>Content Hash</span>
                  <Hash size={16} />
                </div>
                <div className="metric-value" style={{ fontSize: '1.1rem', fontFamily: 'var(--font-mono)' }}>
                  {selectedDataset.content_hash ? selectedDataset.content_hash.substring(0, 10) : 'n/a'}
                </div>
                <div className="metric-sub">SHA-256 reproducibility</div>
              </div>
            </div>

            <div className="card" style={{ padding: '16px 20px', marginBottom: 20, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 600, color: '#fff', fontSize: '1rem', marginBottom: 2 }}>{selectedDataset.name}</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>{selectedDataset.description}</div>
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Created: {new Date(selectedDataset.created_at).toLocaleDateString()}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Examples Table Section */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 600, color: '#fff', fontSize: '1.05rem' }}>Dataset Examples</span>
            <span className="badge badge-neutral">{filteredExamples.length} of {examples.length}</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {/* Split Filter Tabs */}
            <div style={{ display: 'flex', background: 'var(--bg-main)', padding: 3, borderRadius: 8, border: '1px solid var(--border)' }}>
              <button
                className={`btn btn-sm ${splitFilter === '' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ border: 'none', borderRadius: 6 }}
                onClick={() => setSplitFilter('')}
              >
                All ({examples.length})
              </button>
              <button
                className={`btn btn-sm ${splitFilter === 'train' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ border: 'none', borderRadius: 6 }}
                onClick={() => setSplitFilter('train')}
              >
                Tuning Split ({selectedDataset?.train_count || 0})
              </button>
              <button
                className={`btn btn-sm ${splitFilter === 'test' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ border: 'none', borderRadius: 6 }}
                onClick={() => setSplitFilter('test')}
              >
                Held-Out Split ({selectedDataset?.test_count || 0})
              </button>
            </div>

            {/* Search Input */}
            <div style={{ position: 'relative', width: 220 }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: 12, color: 'var(--text-muted)' }} />
              <input
                type="text"
                className="form-input"
                style={{ paddingLeft: 32, paddingRight: 10, height: 36, fontSize: '0.85rem' }}
                placeholder="Search examples..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>

        {filteredExamples.length === 0 ? (
          <div className="empty-state">
            <FileText className="empty-state-icon" />
            <div className="empty-state-title">No examples found</div>
            <div className="empty-state-desc">Try clearing the search or switching splits.</div>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th style={{ width: 80 }}>Split</th>
                  <th>Input Text</th>
                  <th style={{ width: 140 }}>Expected Output</th>
                  <th style={{ width: 150 }}>Characteristics</th>
                </tr>
              </thead>
              <tbody>
                {filteredExamples.map((ex) => (
                  <tr key={ex.id}>
                    <td>
                      <span className={`badge ${ex.split === 'train' ? 'badge-info' : 'badge-success'}`}>
                        {ex.split === 'train' ? 'Tuning' : 'Held-Out'}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-primary)', lineHeight: 1.4 }}>
                      {ex.input_text}
                    </td>
                    <td>
                      <span className="badge badge-neutral" style={{ textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                        {ex.expected_output}
                      </span>
                    </td>
                    <td>
                      {ex.category_tag ? (
                        <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>
                          {ex.category_tag}
                        </span>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>standard</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {uploadModalOpen && (
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
          <div className="card" style={{ maxWidth: 540, width: '100%', maxHeight: '90vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Upload size={20} style={{ color: 'var(--primary)' }} />
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#fff' }}>Upload Custom Dataset</h2>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setUploadModalOpen(false)}
              >
                ✕
              </button>
            </div>

            {uploadError && (
              <div style={{ background: 'var(--danger-bg)', border: '1px solid var(--danger)', color: 'var(--danger)', padding: '10px 14px', borderRadius: 8, marginBottom: 16, fontSize: '0.85rem' }}>
                {uploadError}
              </div>
            )}

            <form onSubmit={handleFileUpload}>
              <div className="form-group">
                <label className="form-label">Dataset File (.csv or .json) *</label>
                <input
                  type="file"
                  accept=".csv,.json"
                  className="form-input"
                  onChange={(e) => setUploadFile(e.target.files[0])}
                  required
                />
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  Supports CSV (with headers) or JSON array of objects.
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Dataset Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. Customer Support Intent Dataset"
                  value={uploadName}
                  onChange={(e) => setUploadName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  className="form-textarea"
                  style={{ minHeight: 70 }}
                  placeholder="Briefly describe the domain, edge cases, and target task..."
                  value={uploadDesc}
                  onChange={(e) => setUploadDesc(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="form-group">
                  <label className="form-label">Input Column Name</label>
                  <input
                    type="text"
                    className="form-input"
                    value={inputCol}
                    onChange={(e) => setInputCol(e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Expected Output Column</label>
                  <input
                    type="text"
                    className="form-input"
                    value={outputCol}
                    onChange={(e) => setOutputCol(e.target.value)}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Tuning / Held-Out Split Ratio</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <input
                    type="range"
                    min="0.5"
                    max="0.9"
                    step="0.05"
                    value={splitRatio}
                    onChange={(e) => setSplitRatio(parseFloat(e.target.value))}
                    style={{ flex: 1 }}
                  />
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', width: 90 }}>
                    {Math.round(splitRatio * 100)}% / {Math.round((1 - splitRatio) * 100)}%
                  </span>
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                  Tuning split is used by the optimizer; Held-out split is kept untouched for final evaluation.
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 24 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setUploadModalOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploading}
                >
                  {uploading ? 'Validating & Uploading...' : 'Upload & Partition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
