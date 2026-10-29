const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const res = await fetch(url, config);
    if (!res.ok) {
      let errorDetail = `HTTP ${res.status}`;
      try {
        const errorJson = await res.json();
        errorDetail = errorJson.detail || errorDetail;
      } catch (e) {
        // use fallback
      }
      throw new Error(errorDetail);
    }
    return await res.json();
  } catch (err) {
    console.error(`API Error on ${endpoint}:`, err);
    throw err;
  }
}

export const api = {
  // Health & Diagnostics
  getHealth: () => request('/api/health'),
  getDashboardStats: () => request('/api/dashboard/stats'),

  // Experiments
  listExperiments: () => request('/api/experiments'),
  getExperiment: (id) => request(`/api/experiments/${id}`),
  createExperiment: (data) => request('/api/experiments', { method: 'POST', body: JSON.stringify(data) }),
  updateExperiment: (id, data) => request(`/api/experiments/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteExperiment: (id) => request(`/api/experiments/${id}`, { method: 'DELETE' }),

  // Prompts
  createPrompt: (data) => request('/api/prompts', { method: 'POST', body: JSON.stringify(data) }),
  getPrompt: (id) => request(`/api/prompts/${id}`),
  updatePrompt: (id, data) => request(`/api/prompts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  runSinglePrompt: (data) => request('/api/prompts/run-single', { method: 'POST', body: JSON.stringify(data) }),

  // Datasets
  listDatasets: () => request('/api/datasets'),
  getDataset: (id) => request(`/api/datasets/${id}`),
  getDatasetExamples: (id, split = '', limit = 100) =>
    request(`/api/datasets/${id}/examples?limit=${limit}${split ? `&split=${split}` : ''}`),
  uploadDataset: async (formData) => {
    const res = await fetch(`${API_BASE_URL}/api/datasets/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  // Evaluations
  createEvaluation: (data) => request('/api/evaluations', { method: 'POST', body: JSON.stringify(data) }),
  listEvaluations: (experimentId = '') =>
    request(`/api/evaluations${experimentId ? `?experiment_id=${experimentId}` : ''}`),
  getEvaluation: (id) => request(`/api/evaluations/${id}`),
  getFailureAnalysis: (id) => request(`/api/evaluations/${id}/failures`),
  compareEvaluations: (baselineId, candidateId, objective = 'maximize_accuracy') =>
    request(`/api/evaluations/compare?objective=${objective}`, {
      method: 'POST',
      body: JSON.stringify({ baseline_eval_id: baselineId, candidate_eval_id: candidateId }),
    }),

  // Agent Runs
  createAgentRun: (data) => request('/api/agent-runs', { method: 'POST', body: JSON.stringify(data) }),
  listAgentRuns: (experimentId = '') =>
    request(`/api/agent-runs${experimentId ? `?experiment_id=${experimentId}` : ''}`),
  getAgentRun: (id) => request(`/api/agent-runs/${id}`),

  // Export URLs
  exportEvaluationUrl: (id, format = 'csv') => `${API_BASE_URL}/api/export/evaluation/${id}?format=${format}`,
  exportExperimentUrl: (id) => `${API_BASE_URL}/api/export/experiment/${id}`,
};
