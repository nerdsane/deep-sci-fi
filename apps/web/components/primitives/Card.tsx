import type { ReactNode } from 'react';

export interface CardProps {
  title?: string;
  subtitle?: string;
  image?: string;
  imagePosition?: 'top' | 'left' | 'right';
  variant?: 'default' | 'elevated' | 'outlined' | 'ghost';
  accent?: 'cyan' | 'purple' | 'none';
  onClick?: () => void;
  children?: ReactNode;
}

export function Card({
  title,
  subtitle,
  image,
  imagePosition = 'top',
  variant = 'default',
  accent = 'none',
  onClick,
  children
}: CardProps) {
  const isClickable = !!onClick;
  const hasHorizontalImage = image && (imagePosition === 'left' || imagePosition === 'right');

  return (
    <div
      className={`dsf-card dsf-card-${variant} dsf-card-accent-${accent} ${isClickable ? 'dsf-card-clickable' : ''} ${hasHorizontalImage ? 'dsf-card-horizontal' : ''}`}
      onClick={onClick}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={isClickable ? (e) => e.key === 'Enter' && onClick?.() : undefined}
      style={hasHorizontalImage ? {
        flexDirection: imagePosition === 'right' ? 'row-reverse' : 'row'
      } : undefined}
    >
      {image && imagePosition === 'top' && (
        <div className="dsf-card-image-container dsf-card-image-top">
          <img src={image} alt="" className="dsf-card-image" />
        </div>
      )}

      {image && (imagePosition === 'left' || imagePosition === 'right') && (
        <div className="dsf-card-image-container dsf-card-image-side">
          <img src={image} alt="" className="dsf-card-image" />
        </div>
      )}

      <div className="dsf-card-content">
        {(title || subtitle) && (
          <div className="dsf-card-header">
            {title && <h3 className="dsf-card-title">{title}</h3>}
            {subtitle && <p className="dsf-card-subtitle">{subtitle}</p>}
          </div>
        )}
        {children && <div className="dsf-card-body">{children}</div>}
      </div>
    </div>
  );
}
