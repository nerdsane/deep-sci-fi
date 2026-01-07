import type { ReactNode } from 'react';

export interface CalloutProps {
  variant?: 'info' | 'warning' | 'quote' | 'rule' | 'tech';
  title?: string;
  children?: ReactNode;
  content?: string;
}

export function Callout({
  variant = 'info',
  title,
  children,
  content
}: CalloutProps) {
  return (
    <div className={`dsf-callout dsf-callout-${variant}`}>
      {title && <div className="dsf-callout-title">{title}</div>}
      <div className="dsf-callout-content">
        {children || content}
      </div>
    </div>
  );
}
