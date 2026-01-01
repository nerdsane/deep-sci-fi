import React, { useEffect, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { api } from '../lib/api';

export function SettingsView() {
  const [activeTab, setActiveTab] = useState('models');
  const [identities, setIdentities] = useState<any[]>([]);
  const [models, setModels] = useState<any[]>([]);
  const [embeddingModels, setEmbeddingModels] = useState<any[]>([]);
  const [providers, setProviders] = useState<any[]>([]);
  const [sandboxConfigs, setSandboxConfigs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAllSettings();
  }, []);

  async function loadAllSettings() {
    try {
      setLoading(true);
      const [identitiesRes, modelsRes, embeddingRes, providersRes, sandboxRes] = await Promise.allSettled([
        api.listIdentities(),
        api.listModels(),
        api.listEmbeddingModels(),
        api.listProviders(),
        api.listSandboxConfigs(),
      ]);

      if (identitiesRes.status === 'fulfilled') {
        setIdentities(Array.isArray(identitiesRes.value) ? identitiesRes.value : identitiesRes.value.items || []);
      }
      if (modelsRes.status === 'fulfilled') {
        setModels(Array.isArray(modelsRes.value) ? modelsRes.value : modelsRes.value.items || []);
      }
      if (embeddingRes.status === 'fulfilled') {
        setEmbeddingModels(Array.isArray(embeddingRes.value) ? embeddingRes.value : embeddingRes.value.items || []);
      }
      if (providersRes.status === 'fulfilled') {
        setProviders(Array.isArray(providersRes.value) ? providersRes.value : providersRes.value.items || []);
      }
      if (sandboxRes.status === 'fulfilled') {
        setSandboxConfigs(Array.isArray(sandboxRes.value) ? sandboxRes.value : sandboxRes.value.items || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading settings...</div>;
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Settings</h2>
        <p className="section-subtitle">
          Models, providers, identities, and sandbox configuration
        </p>
      </div>

      {error && (
        <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      <Tabs.Root value={activeTab} onValueChange={setActiveTab}>
        <Tabs.List className="tabs-list">
          <Tabs.Trigger value="models" className="tab-trigger">
            Models ({models.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="embeddings" className="tab-trigger">
            Embeddings ({embeddingModels.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="providers" className="tab-trigger">
            Providers ({providers.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="identities" className="tab-trigger">
            Identities ({identities.length})
          </Tabs.Trigger>
          <Tabs.Trigger value="sandbox" className="tab-trigger">
            Sandbox ({sandboxConfigs.length})
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="models" className="animate-in">
          <div className="card-list">
            {models.map((model, idx) => (
              <div key={model.id || idx} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {model.name || model.model_name || 'Unknown Model'}
                      </h3>
                      {model.context_window && (
                        <span className="badge badge-neutral text-small font-mono">
                          {model.context_window.toLocaleString()} ctx
                        </span>
                      )}
                    </div>
                    {model.provider && (
                      <div className="text-small text-muted">
                        Provider: <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{model.provider}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {models.length === 0 && (
              <div className="empty-state">No models configured</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="embeddings" className="animate-in">
          <div className="card-list">
            {embeddingModels.map((model, idx) => (
              <div key={model.id || idx} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {model.name || model.model_name || 'Unknown Model'}
                      </h3>
                      {model.dimensions && (
                        <span className="badge badge-neutral text-small font-mono">
                          {model.dimensions}d
                        </span>
                      )}
                    </div>
                    {model.provider && (
                      <div className="text-small text-muted">
                        Provider: <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{model.provider}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {embeddingModels.length === 0 && (
              <div className="empty-state">No embedding models configured</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="providers" className="animate-in">
          <div className="card-list">
            {providers.map((provider) => (
              <div key={provider.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {provider.name}
                      </h3>
                      <span className={`badge ${provider.enabled ? 'badge-success' : 'badge-neutral'}`}>
                        {provider.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    {provider.api_base && (
                      <div className="font-mono text-small" style={{ color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                        {provider.api_base}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {providers.length === 0 && (
              <div className="empty-state">No providers configured</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="identities" className="animate-in">
          <div className="card-list">
            {identities.map((identity) => (
              <div key={identity.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {identity.name || identity.label || 'Untitled'}
                      </h3>
                      {identity.type && (
                        <span className="badge badge-neutral text-small">{identity.type}</span>
                      )}
                    </div>
                    {identity.description && (
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem', marginTop: '0.5rem' }}>
                        {identity.description}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {identities.length === 0 && (
              <div className="empty-state">No identities configured</div>
            )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="sandbox" className="animate-in">
          <div className="card-list">
            {sandboxConfigs.map((config) => (
              <div key={config.id} className="card">
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {config.name || 'Default'}
                      </h3>
                      {config.type && (
                        <span className="badge badge-neutral text-small">{config.type}</span>
                      )}
                    </div>
                    {config.config && (
                      <pre style={{
                        marginTop: '0.75rem',
                        padding: '0.75rem',
                        background: 'rgba(0, 0, 0, 0.3)',
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                        overflow: 'auto',
                        lineHeight: '1.5',
                      }}>
                        {JSON.stringify(config.config, null, 2)}
                      </pre>
                    )}
                  </div>
                </div>
              </div>
            ))}
            {sandboxConfigs.length === 0 && (
              <div className="empty-state">No sandbox configurations found</div>
            )}
          </div>
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
