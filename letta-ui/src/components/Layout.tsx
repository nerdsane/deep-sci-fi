import React from 'react';
import * as Tabs from '@radix-ui/react-tabs';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="app-container">
      {children}
    </div>
  );
}

interface SidebarNavigationProps {
  value: string;
  onValueChange: (value: string) => void;
}

export function SidebarNavigation({ value, onValueChange }: SidebarNavigationProps) {
  const navItems = [
    { id: 'agents', label: 'Agents' },
    { id: 'runs', label: 'Runs' },
    { id: 'trajectories', label: 'Trajectories' },
    // Hidden until fully implemented:
    // { id: 'steps', label: 'Steps' },
    // { id: 'messages', label: 'Messages' },
    // { id: 'jobs', label: 'Jobs' },
    // { id: 'resources', label: 'Resources' },
    // { id: 'settings', label: 'Settings' },
  ];

  return (
    <Tabs.Root value={value} onValueChange={onValueChange} orientation="vertical">
      <div className="sidebar">
        <h1 className="logo">OBSERVE</h1>

        <Tabs.List className="sidebar-nav">
          {navItems.map((item) => (
            <Tabs.Trigger key={item.id} value={item.id} className="nav-item">
              {item.label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
      </div>
    </Tabs.Root>
  );
}
