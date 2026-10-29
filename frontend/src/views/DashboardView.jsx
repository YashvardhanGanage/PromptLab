import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Clock, 
  Layers, 
  CheckCircle2, 
  Bot, 
  AlertTriangle, 
  ArrowUpRight,
  ExternalLink,
  Cpu
} from 'lucide-react';
import { api } from '../api/client';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';

export function DashboardView({ onNavigate }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchStats() {
      try {
        setLoading(true);
        const data = await api.getDashboardStats();
        setStats(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="empty-state">
        <div className="empty-state-title">Loading telemetry...</div>
        <div className="empty-state-desc">Fetching experiment runs and evaluation metrics from PromptLab SQLite database.</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card" style={{ borderColor: 'var(--danger)' }}>
        <div style={{ color: 'var(--danger)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 8 }}>
          <AlertTriangle size={18} /> Error loading dashboard: {error}
        </div>
        <div style={{ marginTop: 8, fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          Ensure the PromptLab FastAPI backend is running at http://127.0.0.1:8000.
        </div>
      </div>
    );
  }

  const bestPrompt = stats?.best_prompt;

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Operational Telemetry</h1>
          <p className="page-subtitle">Evidence-based prompt performance metrics, regressions, and optimization progress.</p>
        </div>
        <button className="btn btn-primary" onClick={() => onNavigate('promptlab')}>
          <Bot size={16} /> Open Prompt Lab
        </button>
      </div>

      {/* Metric Cards */}
      <div className="grid-cards">
        <div className="metric-card">
          <div className="metric-header">
            <span>Total Experiments</span>
            <Layers size={18} color="var(--primary)" />
          </div>
          <div className="metric-value">{stats?.total_experiments || 0}</div>
          <div className="metric-sub">Persistent workspace projects</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Evaluation Runs</span>
            <CheckCircle2 size={18} color="var(--success)" />
          </div>
          <div className="metric-value">{stats?.total_evaluations || 0}</div>
          <div className="metric-sub">Across benchmark partitions</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Agent Runs</span>
            <Bot size={18} color="var(--cyan)" />
          </div>
          <div className="metric-value">{stats?.total_agent_runs || 0}</div>
          <div className="metric-sub">Autonomous optimization cycles</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Top Prompt Quality</span>
            <TrendingUp size={18} color="var(--warning)" />
          </div>
          <div className="metric-value">
            {bestPrompt ? `${(bestPrompt.accuracy * 100).toFixed(1)}%` : '—'}
          </div>
          <div className="metric-sub">
            {bestPrompt ? bestPrompt.name : 'No evaluations yet'}
          </div>
        </div>
      </div>

      {/* Telemetry Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        <div className="card">
          <div className="card-title">
            <span>Accuracy Evolution Trend</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Latest evaluations</span>
          </div>
          {stats?.trends && stats.trends.length > 0 ? (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats.trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e384d" />
                  <XAxis dataKey="prompt" stroke="#6b7280" fontSize={11} tickLine={false} />
                  <YAxis stroke="#6b7280" fontSize={11} domain={[0, 100]} tickLine={false} unit="%" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#2e384d', borderRadius: 8 }}
                    itemStyle={{ color: '#6366f1' }}
                  />
                  <Line type="monotone" dataKey="accuracy" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '36px 0' }}>
              <div className="empty-state-desc">Run your first prompt evaluation to render trend lines.</div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">
            <span>Inference Latency Trend</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Average latency (ms)</span>
          </div>
          {stats?.trends && stats.trends.length > 0 ? (
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats.trends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2e384d" />
                  <XAxis dataKey="prompt" stroke="#6b7280" fontSize={11} tickLine={false} />
                  <YAxis stroke="#6b7280" fontSize={11} tickLine={false} unit="ms" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#111827', borderColor: '#2e384d', borderRadius: 8 }}
                    itemStyle={{ color: '#06b6d4' }}
                  />
                  <Line type="monotone" dataKey="latency_ms" stroke="#06b6d4" strokeWidth={2.5} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '36px 0' }}>
              <div className="empty-state-desc">Evaluate prompts to monitor latency regressions.</div>
            </div>
          )}
        </div>
      </div>

      {/* Regressions and Latest Evaluations */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div className="card">
          <div className="card-title">
            <span>Observed Candidate Regressions</span>
            <span className="badge badge-danger">{stats?.recent_regressions?.length || 0} Detected</span>
          </div>
          {stats?.recent_regressions && stats.recent_regressions.length > 0 ? (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Candidate Prompt</th>
                    <th>Strategy</th>
                    <th>Rejection Rationale</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_regressions.map((reg, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 600, color: '#fff' }}>{reg.prompt_name}</td>
                      <td><span className="badge badge-warning">{reg.strategy}</span></td>
                      <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{reg.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-state-desc">No regressions observed. Candidate rejection guardrails are active.</div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-title">
            <span>Latest Evaluation Runs</span>
            <button className="btn btn-secondary btn-sm" onClick={() => onNavigate('evaluations')}>
              View All <ArrowUpRight size={14} />
            </button>
          </div>
          {stats?.latest_evaluations && stats.latest_evaluations.length > 0 ? (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Prompt</th>
                    <th>Accuracy</th>
                    <th>F1 Score</th>
                    <th>Avg Latency</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.latest_evaluations.map((ev) => (
                    <tr key={ev.id}>
                      <td style={{ fontWeight: 600, color: '#fff' }}>{ev.prompt_name}</td>
                      <td>
                        <span className={`badge ${ev.accuracy >= 0.8 ? 'badge-success' : (ev.accuracy >= 0.6 ? 'badge-warning' : 'badge-danger')}`}>
                          {(ev.accuracy * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td>{(ev.macro_f1 * 100).toFixed(1)}%</td>
                      <td>{ev.avg_latency_ms.toFixed(1)}ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '24px 0' }}>
              <div className="empty-state-desc">No evaluations recorded yet. Run your first evaluation in Prompt Lab.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
