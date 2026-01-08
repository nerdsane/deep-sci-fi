interface WorldContextProps {
  contextType: 'rule' | 'character' | 'location' | 'tech';
  title?: string;
  content?: string;
  isVisible: boolean;
  'data-section-index'?: number;
  className?: string;
}

const CONTEXT_ICONS: Record<string, string> = {
  rule: '⚖',
  character: '◉',
  location: '◇',
  tech: '⬡'
};

const CONTEXT_LABELS: Record<string, string> = {
  rule: 'World Rule',
  character: 'Character',
  location: 'Location',
  tech: 'Technology'
};

export function WorldContext({
  contextType,
  title,
  content,
  isVisible,
  ...props
}: WorldContextProps) {
  const icon = CONTEXT_ICONS[contextType] || '◈';
  const label = CONTEXT_LABELS[contextType] || 'World Context';

  return (
    <aside
      {...props}
      className={`world-context context-${contextType} ${isVisible ? 'visible' : ''}`}
    >
      <div className="context-header">
        <span className="context-icon">{icon}</span>
        <span className="context-label">{label}</span>
      </div>
      {title && <h4 className="context-title">{title}</h4>}
      {content && <p className="context-content">{content}</p>}
      <div className="context-glow" />
    </aside>
  );
}
