import React, { useEffect, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { api } from '../lib/api';

export function ResourcesView() {
  const [activeTab, setActiveTab] = useState('blocks');
  const [blocks, setBlocks] = useState<any[]>([]);
  const [tools, setTools] = useState<any[]>([]);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [sources, setSources] = useState<any[]>([]);
  const [folders, setFolders] = useState<any[]>([]);
  const [archives, setArchives] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAllResources();
  }, []);

  async function loadAllResources() {
    try {
      setLoading(true);
      const [blocksRes, toolsRes, mcpRes, sourcesRes, foldersRes, archivesRes] = await Promise.allSettled([
        api.listBlocks(),
        api.listTools(),
        api.listMCPServers(),
        api.listSources(),
        api.listFolders(),
        api.listArchives(),
      ]);

      if (blocksRes.status === 'fulfilled') {
        setBlocks(Array.isArray(blocksRes.value) ? blocksRes.value : blocksRes.value.items || []);
      }
      if (toolsRes.status === 'fulfilled') {
        setTools(Array.isArray(toolsRes.value) ? toolsRes.value : toolsRes.value.items || []);
      }
      if (mcpRes.status === 'fulfilled') {
        setMcpServers(Array.isArray(mcpRes.value) ? mcpRes.value : mcpRes.value.items || []);
      }
      if (sourcesRes.status === 'fulfilled') {
        setSources(Array.isArray(sourcesRes.value) ? sourcesRes.value : sourcesRes.value.items || []);
      }
      if (foldersRes.status === 'fulfilled') {
        setFolders(Array.isArray(foldersRes.value) ? foldersRes.value : foldersRes.value.items || []);
      }
      if (archivesRes.status === 'fulfilled') {
        setArchives(Array.isArray(archivesRes.value) ? archivesRes.value : archivesRes.value.items || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load resources');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading resources...</div>;
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Resources</h2>
        <p className="section-subtitle">
          Memory blocks, tools, MCP servers, and data sources
        </p>
      </div>

      {error && (
        <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="tabs-list">
          <Tabs.Trigger value="blocks" className="tab-trigger">
            Memory Blocks ({blocks.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="tools" className="tab-trigger">
            Tools ({tools.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="mcp" className="tab-trigger">
            MCP Servers ({mcpServers.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="sources" className="tab-trigger">
            Sources ({sources.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="folders" className="tab-trigger">
            Folders ({folders.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="archives" className="tab-trigger">
            Archives ({archives.length})
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="blocks" className="animate-in">
          <div className="card-list">
            {blocks.map((block) => (
              <div key={block.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {block.label || block.name || 'Untitled'}
                      </h3>
                      <span className="badge badge-neutral font-mono text-small">
                        {block.template_name || block.type || 'block'}
                      </span>
                    </div>
                    {block.value && (
                      <div style={{
                        marginTop: '0.75rem',
                        padding: '0.75rem',
                        background: 'rgba(0, 255, 136, 0.03)',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.875rem',
                        color: 'var(--text-secondary)',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                      }}>
                        {block.value}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {blocks.length === 0 && (
              <div className="empty-state">No memory blocks found</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="tools" className="animate-in">
          <div className="card-list">
            {tools.map((tool) => (
              <div key={tool.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {tool.name}
                      </h3>
                      {tool.tags && tool.tags.length > 0 && (
                        <div className="flex gap-2">
                          {tool.tags.slice(0, 3).map((tag: string) => (
                            <span key={tag} className="badge badge-neutral text-small">{tag}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    {tool.description && (
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem', marginTop: '0.5rem' }}>
                        {tool.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {tools.length === 0 && (
              <div className="empty-state">No tools found</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="mcp" className="animate-in">
          <div className="card-list">
            {mcpServers.map((server) => (
              <div key={server.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {server.name}
                      </h3>
                      <span className={`badge ${server.connected ? 'badge-success' : 'badge-failure'}`}>
                        {server.connected ? 'Connected' : 'Disconnected'}
                      </span>
                    </div>
                    {server.description && (
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem', marginTop: '0.5rem' }}>
                        {server.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {mcpServers.length === 0 && (
              <div className="empty-state">No MCP servers configured</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="sources" className="animate-in">
          <div className="card-list">
            {sources.map((source) => (
              <div key={source.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {source.name}
                      </h3>
                      {source.metadata?.file_count !== undefined && (
                        <span className="text-small text-muted font-mono">
                          {source.metadata.file_count} files
                        </span>
                      )}
                    </div>
                    {source.description && (
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem', marginTop: '0.5rem' }}>
                        {source.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {sources.length === 0 && (
              <div className="empty-state">No sources found</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="folders" className="animate-in">
          <div className="card-list">
            {folders.map((folder) => (
              <div key={folder.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {folder.name}
                      </h3>
                      {folder.metadata?.file_count !== undefined && (
                        <span className="text-small text-muted font-mono">
                          {folder.metadata.file_count} files
                        </span>
                      )}
                    </div>
                    {folder.path && (
                      <p className="font-mono text-small" style={{ color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                        {folder.path}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {folders.length === 0 && (
              <div className="empty-state">No folders found</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="archives" className="animate-in">
          <div className="card-list">
            {archives.map((archive) => (
              <div key={archive.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {archive.name || 'Untitled Archive'}
                      </h3>
                      {archive.metadata?.passage_count !== undefined && (
                        <span className="text-small text-muted font-mono">
                          {archive.metadata.passage_count} passages
                        </span>
                      )}
                    </div>
                    {archive.description && (
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem', marginTop: '0.5rem' }}>
                        {archive.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {archives.length === 0 && (
              <div className="empty-state">No archives found</div>
            )}
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
