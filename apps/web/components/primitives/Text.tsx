interface TextProps {
  content: string;
  variant?: 'body' | 'heading' | 'caption';
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  color?: string;
}

export function Text({ content, variant = 'body', size = 'md', color }: TextProps) {
  const Tag = variant === 'heading' ? 'h3' : 'p';

  const className = variant === 'heading'
    ? 'subsection-title'
    : '';

  const style: React.CSSProperties = {
    fontSize: size === 'sm' ? 'var(--text-sm)' :
              size === 'md' ? 'var(--text-base)' :
              size === 'lg' ? 'var(--text-lg)' :
              size === 'xl' ? 'var(--text-xl)' :
              size === '2xl' ? 'var(--text-2xl)' : undefined,
    color: color || undefined
  };

  return <Tag className={className} style={style}>{content}</Tag>;
}
