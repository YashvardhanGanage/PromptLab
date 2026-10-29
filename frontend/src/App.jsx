import React, { useState } from 'react';
import { Navigation } from './components/Navigation';
import { DashboardView } from './views/DashboardView';
import { PromptLabView } from './views/PromptLabView';
import { DatasetsView } from './views/DatasetsView';
import { EvaluationsView } from './views/EvaluationsView';
import { AgentRunsView } from './views/AgentRunsView';
import { ExperimentsView } from './views/ExperimentsView';
import { SettingsView } from './views/SettingsView';

export function App() {
  const [activeTab, setActiveTab] = useState('dashboard');

  const handleNavigate = (tab) => {
    setActiveTab(tab);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="app-container">
      <Navigation activeTab={activeTab} setActiveTab={setActiveTab} />
      
      <main className="main-content">
        {activeTab === 'dashboard' && <DashboardView onNavigate={handleNavigate} />}
        {activeTab === 'promptlab' && <PromptLabView onNavigate={handleNavigate} />}
        {activeTab === 'datasets' && <DatasetsView onNavigate={handleNavigate} />}
        {activeTab === 'evaluations' && <EvaluationsView onNavigate={handleNavigate} />}
        {activeTab === 'agent' && <AgentRunsView onNavigate={handleNavigate} />}
        {activeTab === 'experiments' && <ExperimentsView onNavigate={handleNavigate} />}
        {activeTab === 'settings' && <SettingsView onNavigate={handleNavigate} />}
      </main>
    </div>
  );
}

export default App;
