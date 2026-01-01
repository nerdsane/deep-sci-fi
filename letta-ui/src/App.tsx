import React, { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { Layout, SidebarNavigation } from './components/Layout';
import { AgentsView } from './components/AgentsView';
import { TrajectoriesView } from './components/TrajectoriesView';
import { RunsView } from './components/RunsView';

export default function App() {
  const [activeTab, setActiveTab] = useState('agents');

  return (
    <Layout>
      <Tabs.Root value={activeTab} onValueChange={setActiveTab} orientation="vertical">
        <SidebarNavigation value={activeTab} onValueChange={setActiveTab} />

        <main className="main-content">
          <Tabs.Content value="agents" className="animate-in">
            <AgentsView />
          </Tabs.Content>

          <Tabs.Content value="runs" className="animate-in">
            <RunsView />
          </Tabs.Content>

          <Tabs.Content value="trajectories" className="animate-in">
            <TrajectoriesView />
          </Tabs.Content>

          <Tabs.Content value="messages" className="animate-in">
            <div className="empty-state">
              <h3 style={{ fontSize: '1.5rem', marginBottom: '0.75rem', color: 'var(--text)' }}>Messages</h3>
              <p>Message visualization coming soon</p>
            </div>
          </Tabs.Content>

          <Tabs.Content value="resources" className="animate-in">
            <div className="empty-state">
              <h3 style={{ fontSize: '1.5rem', marginBottom: '0.75rem', color: 'var(--text)' }}>Resources</h3>
              <p>Memory blocks, tools, and MCP servers coming soon</p>
            </div>
          </Tabs.Content>

          <Tabs.Content value="settings" className="animate-in">
            <div className="empty-state">
              <h3 style={{ fontSize: '1.5rem', marginBottom: '0.75rem', color: 'var(--text)' }}>Settings</h3>
              <p>Configuration settings coming soon</p>
            </div>
          </Tabs.Content>
        </main>
      </Tabs.Root>
    </Layout>
  );
}
