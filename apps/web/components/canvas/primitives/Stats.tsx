export interface StatItem {
  value: string | number;
  label: string;
  trend?: 'up' | 'down' | 'neutral';
  accent?: 'cyan' | 'purple' | 'default';
}

export interface StatsProps {
  items: StatItem[];
  columns?: 2 | 3 | 4 | 'auto';
  variant?: 'default' | 'compact' | 'large';
}

export function Stats({
  items,
  columns = 'auto',
  variant = 'default'
}: StatsProps) {
  const gridCols = columns === 'auto'
    ? `repeat(auto-fit, minmax(120px, 1fr))`
    : `repeat(${columns}, 1fr)`;

  return (
    <div
      className={`dsf-stats dsf-stats-${variant}`}
      style={{ gridTemplateColumns: gridCols }}
    >
      {items.map((item, index) => (
        <div
          key={index}
          className={`dsf-stat dsf-stat-accent-${item.accent || 'default'}`}
        >
          <div className="dsf-stat-value">
            {item.trend === 'up' && <span className="dsf-stat-trend-up">↑</span>}
            {item.trend === 'down' && <span className="dsf-stat-trend-down">↓</span>}
            {item.value}
          </div>
          <div className="dsf-stat-label">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
