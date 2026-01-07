export interface TimelineEvent {
  id?: string;
  date?: string;
  year?: string | number;
  title: string;
  description?: string;
  icon?: string;
  status?: 'completed' | 'current' | 'upcoming';
  accent?: 'cyan' | 'purple' | 'default';
}

export interface TimelineProps {
  events: TimelineEvent[];
  orientation?: 'vertical' | 'horizontal';
  variant?: 'default' | 'compact' | 'detailed';
  showConnectors?: boolean;
}

export function Timeline({
  events,
  orientation = 'vertical',
  variant = 'default',
  showConnectors = true
}: TimelineProps) {
  if (events.length === 0) {
    return (
      <div className="dsf-timeline-empty">
        No events to display
      </div>
    );
  }

  if (orientation === 'horizontal') {
    return (
      <div className={`dsf-timeline dsf-timeline-horizontal dsf-timeline-${variant}`}>
        <div className="dsf-timeline-track">
          {showConnectors && <div className="dsf-timeline-line" />}
          {events.map((event, index) => (
            <div
              key={event.id || index}
              className={`dsf-timeline-item dsf-timeline-status-${event.status || 'default'} dsf-timeline-accent-${event.accent || 'default'}`}
            >
              <div className="dsf-timeline-marker">
                {event.icon ? (
                  <span className="dsf-timeline-icon">{event.icon}</span>
                ) : (
                  <span className="dsf-timeline-dot" />
                )}
              </div>
              <div className="dsf-timeline-content">
                {(event.date || event.year) && (
                  <div className="dsf-timeline-date">{event.date || event.year}</div>
                )}
                <div className="dsf-timeline-title">{event.title}</div>
                {variant === 'detailed' && event.description && (
                  <div className="dsf-timeline-description">{event.description}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Vertical orientation (default)
  return (
    <div className={`dsf-timeline dsf-timeline-vertical dsf-timeline-${variant}`}>
      {events.map((event, index) => (
        <div
          key={event.id || index}
          className={`dsf-timeline-item dsf-timeline-status-${event.status || 'default'} dsf-timeline-accent-${event.accent || 'default'}`}
        >
          <div className="dsf-timeline-marker-container">
            <div className="dsf-timeline-marker">
              {event.icon ? (
                <span className="dsf-timeline-icon">{event.icon}</span>
              ) : (
                <span className="dsf-timeline-dot" />
              )}
            </div>
            {showConnectors && index < events.length - 1 && (
              <div className="dsf-timeline-connector" />
            )}
          </div>
          <div className="dsf-timeline-content">
            {(event.date || event.year) && (
              <div className="dsf-timeline-date">{event.date || event.year}</div>
            )}
            <div className="dsf-timeline-title">{event.title}</div>
            {event.description && (
              <div className="dsf-timeline-description">{event.description}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
