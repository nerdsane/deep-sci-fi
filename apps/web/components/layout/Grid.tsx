import type { ReactNode } from 'react';

export interface GridProps {
  columns?: number | 'auto';
  rows?: number | 'auto';
  gap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  columnGap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  rowGap?: 'none' | 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  minChildWidth?: string;
  align?: 'start' | 'center' | 'end' | 'stretch';
  justify?: 'start' | 'center' | 'end' | 'stretch';
  children?: ReactNode;
}

const gapMap = {
  none: '0',
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px'
};

export function Grid({
  columns = 'auto',
  rows = 'auto',
  gap = 'md',
  columnGap,
  rowGap,
  minChildWidth = '200px',
  align = 'stretch',
  justify = 'stretch',
  children
}: GridProps) {
  const gridTemplateColumns =
    columns === 'auto'
      ? `repeat(auto-fill, minmax(${minChildWidth}, 1fr))`
      : `repeat(${columns}, 1fr)`;

  const gridTemplateRows =
    rows === 'auto' ? 'auto' : `repeat(${rows}, 1fr)`;

  return (
    <div
      className="dsf-grid"
      style={{
        display: 'grid',
        gridTemplateColumns,
        gridTemplateRows,
        gap: gapMap[gap],
        columnGap: columnGap ? gapMap[columnGap] : undefined,
        rowGap: rowGap ? gapMap[rowGap] : undefined,
        alignItems: align,
        justifyItems: justify
      }}
    >
      {children}
    </div>
  );
}
