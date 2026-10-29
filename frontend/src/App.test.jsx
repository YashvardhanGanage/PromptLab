import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { App } from './App';
import { api } from './api/client';

// Mock the API client
vi.mock('./api/client', () => ({
  api: {
    getHealth: vi.fn().mockResolvedValue({
      status: 'healthy',
      database: 'connected',
      llm: { status: 'mock_mode', default_model: 'llama3.2:1b' }
    }),
    getDashboardStats: vi.fn().mockResolvedValue({
      total_experiments: 2,
      total_prompts: 5,
      total_evaluations: 8,
      avg_accuracy: 0.88,
      recent_regressions: [],
      accuracy_trend: [
        { run_date: '2026-10-28', accuracy: 0.75 },
        { run_date: '2026-10-29', accuracy: 0.88 }
      ],
      recent_evaluations: []
    }),
    listExperiments: vi.fn().mockResolvedValue([
      { id: 'exp-1', name: 'Sentiment Benchmark', task_type: 'sentiment_classification', prompt_count: 2 }
    ]),
    getExperiment: vi.fn().mockResolvedValue({
      id: 'exp-1',
      name: 'Sentiment Benchmark',
      prompts: [
        { id: 'p-1', version: 1, name: 'Baseline Prompt', system_prompt: 'Classify sentiment.', user_template: '{input}' }
      ]
    }),
    listDatasets: vi.fn().mockResolvedValue([
      { id: 'ds-1', name: 'Starter Benchmark', total_examples: 30, train_count: 20, test_count: 10 }
    ]),
    getDataset: vi.fn().mockResolvedValue({
      id: 'ds-1',
      name: 'Starter Benchmark',
      total_examples: 30,
      train_count: 20,
      test_count: 10
    }),
    getDatasetExamples: vi.fn().mockResolvedValue({
      examples: [
        { id: 'ex-1', input_text: 'Great food', expected_output: 'positive', split: 'train' }
      ]
    }),
    listEvaluations: vi.fn().mockResolvedValue([]),
    listAgentRuns: vi.fn().mockResolvedValue([]),
    exportEvaluationUrl: vi.fn().mockReturnValue('http://127.0.0.1:8000/api/export/evaluation/1'),
    exportExperimentUrl: vi.fn().mockReturnValue('http://127.0.0.1:8000/api/export/experiment/1')
  }
}));

describe('PromptLab Frontend Navigation & Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders brand identity and navigation tabs', async () => {
    render(<App />);
    expect(screen.getByText('PromptLab')).toBeInTheDocument();
    expect(screen.getByText('Agentic')).toBeInTheDocument();

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Prompt Lab')).toBeInTheDocument();
    expect(screen.getByText('Datasets')).toBeInTheDocument();
    expect(screen.getByText('Evaluations')).toBeInTheDocument();
    expect(screen.getByText('Agent Optimizer')).toBeInTheDocument();
    expect(screen.getByText('Experiments')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('navigates to Datasets view when Datasets tab is clicked', async () => {
    render(<App />);
    const datasetsTab = screen.getByText('Datasets');
    fireEvent.click(datasetsTab);

    await waitFor(() => {
      expect(screen.getByText('Dataset Management')).toBeInTheDocument();
      expect(screen.getByText('Upload Dataset')).toBeInTheDocument();
    });
  });

  it('navigates to Agent Optimizer view when Agent tab is clicked', async () => {
    render(<App />);
    const agentTab = screen.getByText('Agent Optimizer');
    fireEvent.click(agentTab);

    await waitFor(() => {
      expect(screen.getByText('Agentic Prompt Optimizer')).toBeInTheDocument();
      expect(screen.getByText(/Bounded Optimization & Data Isolation Guarantee/i)).toBeInTheDocument();
    });
  });

  it('navigates to Settings view and displays diagnostics', async () => {
    render(<App />);
    const settingsTab = screen.getByText('Settings');
    fireEvent.click(settingsTab);

    await waitFor(() => {
      expect(screen.getByText('Settings & Diagnostics')).toBeInTheDocument();
      expect(screen.getByText('SQLite (WAL)')).toBeInTheDocument();
    });
  });
});
