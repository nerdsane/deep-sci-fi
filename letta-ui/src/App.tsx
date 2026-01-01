import React, { useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { Layout, SidebarNavigation } from './components/Layout';
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
            <MessagesView />
          </Tabs.Content>

          <Tabs.Content value="steps" className="animate-in">
            <StepsView />
          </Tabs.Content>

          <Tabs.Content value="jobs" className="animate-in">
            <JobsView />
          </Tabs.Content>

          <Tabs.Content value="resources" className="animate-in">
            <ResourcesView />
          </Tabs.Content>

          <Tabs.Content value="settings" className="animate-in">
            <SettingsView />
          </Tabs.Content>
        </main>
      </Tabs.Root>
    </Layout>
  );
}
