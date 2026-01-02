import React from 'react';

interface SkeletonProps {
  width?: string;
  height?: string;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = '1rem', style }: SkeletonProps) {
  return (
    <div
      style={{
        width,
        height,
        background: 'linear-gradient(90deg, rgba(255, 255, 255, 0.05) 25%, rgba(255, 255, 255, 0.08) 50%, rgba(255, 255, 255, 0.05) 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.5s infinite',
        borderRadius: '4px',
        ...style,
      }}
    />
  );
}

export function TrajectoryListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div
      style={{
        background: 'rgba(255, 255, 255, 0.01)',
        border: '1px solid var(--border-subtle)',
        overflow: 'hidden',
      }}
    >
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          style={{
            padding: '1rem 1.5rem',
            borderBottom: index < count - 1 ? '1px solid var(--border-subtle)' : 'none',
            borderLeft: '3px solid transparent',
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <Skeleton width="80px" height="24px" />
            <Skeleton width="100px" height="20px" />
          </div>
          <Skeleton width="100%" height="16px" style={{ marginBottom: '0.5rem' }} />
          <Skeleton width="80%" height="16px" style={{ marginBottom: '0.75rem' }} />
          <div className="flex justify-between items-center">
            <Skeleton width="60px" height="14px" />
            <Skeleton width="100px" height="14px" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function TrajectoryDetailSkeleton() {
  return (
    <div className="card" style={{ position: 'sticky', top: '1.5rem', maxHeight: 'calc(100vh - 6rem)', overflow: 'auto' }}>
      {/* Header */}
      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
        <div className="flex items-center gap-3 mb-3">
          <Skeleton width="80px" height="24px" />
          <Skeleton width="100px" height="20px" />
        </div>
        <Skeleton width="100%" height="16px" style={{ marginBottom: '0.5rem' }} />
        <Skeleton width="90%" height="16px" style={{ marginBottom: '0.5rem' }} />
        <Skeleton width="80%" height="16px" />
      </div>

      {/* Metadata */}
      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
        <Skeleton width="100px" height="20px" style={{ marginBottom: '1rem' }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i}>
              <Skeleton width="60px" height="12px" style={{ marginBottom: '0.5rem' }} />
              <Skeleton width="80px" height="16px" />
            </div>
          ))}
        </div>
      </div>

      {/* Outcome */}
      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
        <Skeleton width="140px" height="20px" style={{ marginBottom: '1rem' }} />
        <Skeleton width="80px" height="12px" style={{ marginBottom: '0.5rem' }} />
        <Skeleton width="60px" height="20px" />
      </div>

      {/* Turns */}
      <div>
        <Skeleton width="180px" height="20px" style={{ marginBottom: '1rem' }} />
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            style={{
              padding: '1rem',
              background: 'rgba(255, 255, 255, 0.02)',
              border: '1px solid var(--border-subtle)',
              marginBottom: i < 2 ? '1rem' : 0,
            }}
          >
            <div className="flex justify-between items-center mb-3">
              <Skeleton width="60px" height="16px" />
              <Skeleton width="120px" height="14px" />
            </div>
            <Skeleton width="100%" height="16px" style={{ marginBottom: '0.5rem' }} />
            <Skeleton width="90%" height="16px" style={{ marginBottom: '0.5rem' }} />
            <Skeleton width="70%" height="16px" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function StatsSkeleton() {
  return (
    <div className="stats-grid">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="stat-card">
          <Skeleton width="60px" height="32px" style={{ marginBottom: '0.5rem' }} />
          <Skeleton width="100px" height="14px" />
        </div>
      ))}
    </div>
  );
}
