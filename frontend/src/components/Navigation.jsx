import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  FlaskConical, 
  Database, 
  CheckCircle2, 
  Bot, 
  Layers, 
  Settings,
  Sparkles,
  Server
} from 'lucide-react';
import { api } from '../api/client';

export function Navigation({ activeTab, setActiveTab }) {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    async function loadHealth() {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch (err) {
        setHealth({ status: 'offline', llm: { status: 'offline', default_model: 'unknown' } });
      }
    }
    loadHealth();
    const interval = setInterval(loadHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'promptlab', label: 'Prompt Lab', icon: FlaskConical },
    { id: 'datasets', label: 'Datasets', icon: Database },
    { id: 'evaluations', label: 'Evaluations', icon: CheckCircle2 },
    { id: 'agent', label: 'Agent Optimizer', icon: Bot, highlight: true },
    { id: 'experiments', label: 'Experiments', icon: Layers },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  const llmStatus = health?.llm?.status || 'loading';
  const isOnline = llmStatus === 'connected' || llmStatus === 'mock_mode';
  const modelName = health?.llm?.default_model || 'llama3.2:1b';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-icon">
          <Sparkles size={18} />
        </div>
        <div>
          <span className="brand-title">PromptLab</span>
          <span className="brand-badge">Agentic</span>
        </div>
      </div>

      <nav className="nav-links">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <Icon size={18} />
              <span>{item.label}</span>
              {item.highlight && !isActive && (
                <span style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: '#6366f1' }} />
              )}
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="model-pill" title={health?.llm?.mode || 'Diagnostics'}>
          <span className={`status-dot ${!isOnline ? 'offline' : ''}`} />
          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            <div style={{ fontWeight: 600, fontSize: '0.75rem', color: '#fff' }}>{modelName}</div>
            <div style={{ fontSize: '0.7rem', color: isOnline ? '#10b981' : '#ef4444' }}>
              {llmStatus === 'connected' ? 'Ollama Online' : (llmStatus === 'mock_mode' || health?.llm?.mode === 'mock_deterministic' ? 'Mock Deterministic' : 'Offline / Mock')}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
