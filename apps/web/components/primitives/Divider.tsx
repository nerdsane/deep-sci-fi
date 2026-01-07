export interface DividerProps {
  variant?: 'default' | 'accent' | 'dashed';
  spacing?: 'sm' | 'md' | 'lg';
  label?: string;
}

export function Divider({
  variant = 'default',
  spacing = 'md',
  label
}: DividerProps) {
  const spacingMap = {
    sm: 'var(--space-2)',
    md: 'var(--space-4)',
    lg: 'var(--space-6)'
  };

  if (label) {
    return (
      <div
        className={`dsf-divider-labeled dsf-divider-${variant}`}
        style={{ margin: `${spacingMap[spacing]} 0` }}
      >
        <span className="dsf-divider-line" />
        <span className="dsf-divider-label">{label}</span>
        <span className="dsf-divider-line" />
      </div>
    );
  }

  return (
    <div
      className={`dsf-divider dsf-divider-${variant}`}
      style={{ margin: `${spacingMap[spacing]} 0` }}
    />
  );
}
