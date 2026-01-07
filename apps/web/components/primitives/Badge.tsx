export interface BadgeProps {
  label: string;
  variant?: 'default' | 'cyan' | 'purple' | 'success' | 'warning' | 'error';
  size?: 'sm' | 'md' | 'lg';
  icon?: string;
}

export function Badge({
  label,
  variant = 'default',
  size = 'md',
  icon
}: BadgeProps) {
  return (
    <span className={`dsf-badge dsf-badge-${variant} dsf-badge-${size}`}>
      {icon && <span className="dsf-badge-icon">{icon}</span>}
      {label}
    </span>
  );
}
