import React, { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { Layout, SidebarNavigation } from './components/Layout';
import { ErrorBoundary } from './components/ErrorBoundary';
import { AgentsView } from './components/AgentsView';
import { TrajectoriesView } from './components/TrajectoriesView';
import { RunsView } from './components/RunsView';
import { MessagesView } from './components/MessagesView';
import { ResourcesView } from './components/ResourcesView';
import { StepsView } from './components/StepsView';
import { JobsView } from './components/JobsView';
import { SettingsView } from './components/SettingsView';

export default function App() {
  const [activeTab, setActiveTab] = useState('agents');
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);

  // Handler for navigating to a specific agent from other views
  const handleNavigateToAgent = (agentId: string) => {
    setSelectedAgentId(agentId);
    setActiveTab('agents');
  };

  return (
    <ErrorBoundary>
      <Layout>
        <Tabs.Root value={activeTab} onValueChange={setActiveTab} orientation="vertical">
          <SidebarNavigation value={activeTab} onValueChange={setActiveTab} />

          <main className="main-content">
            <ErrorBoundary>
              <Tabs.Content value="agents" className="animate-in">
                <AgentsView initialSelectedAgentId={selectedAgentId} onAgentSelected={() => setSelectedAgentId(null)} />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="runs" className="animate-in">
                <RunsView />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="trajectories" className="animate-in">
                <TrajectoriesView onNavigateToAgent={handleNavigateToAgent} />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="messages" className="animate-in">
                <MessagesView />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="steps" className="animate-in">
                <StepsView />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="jobs" className="animate-in">
                <JobsView />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="resources" className="animate-in">
                <ResourcesView />
              </Tabs.Content>
            </ErrorBoundary>

            <ErrorBoundary>
              <Tabs.Content value="settings" className="animate-in">
                <SettingsView />
              </Tabs.Content>
            </ErrorBoundary>
          </main>
        </Tabs.Root>
      </Layout>
    </ErrorBoundary>
  );
}
