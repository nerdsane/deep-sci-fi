'use client';

import { ReactNode } from 'react';
import { PersistentChatSidebar } from './PersistentChatSidebar';
import './layout.css';

interface AppShellProps {
  children: ReactNode;
}

/**
 * AppShell - Main layout wrapper for the entire app
 *
 * Layout:
 * ┌──────────────┬─────────────────────────────────────┐
 * │ Chat Sidebar │ Canvas/Content Area                 │
 * │ (Left)       │ (Right)                             │
 * │ 400px fixed  │ Flexible width                      │
 * │              │                                     │
 * │ Persistent:  │ - Worlds list                       │
 * │ - Messages   │ - World detail                      │
 * │ - Input box  │ - Story reader                      │
 * │ - History    │                                     │
 * │              │ Navigation:                         │
 * │ Agent:       │ - Click cards → updates canvas      │
 * │ - User Agent │ - Chat commands → updates canvas    │
 * │ - World Agent│ - Breadcrumbs at top                │
 * │ (seamless)   │                                     │
 * └──────────────┴─────────────────────────────────────┘
 *
 * The chat sidebar persists across all navigation.
 * The canvas area changes based on the current route.
 */
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="app-shell">
      <PersistentChatSidebar />
      <div className="canvas-area">
        {children}
      </div>
    </div>
  );
}
