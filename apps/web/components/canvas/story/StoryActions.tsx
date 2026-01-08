interface Branch {
  id: string;
  label: string;
  preview?: string;
}

interface StoryActionsProps {
  canContinue?: boolean;
  branches?: Branch[];
  onContinue?: () => void;
  onBranch?: (branchId: string) => void;
}

export function StoryActions({
  canContinue,
  branches,
  onContinue,
  onBranch
}: StoryActionsProps) {
  const hasBranches = branches && branches.length > 0;

  if (!canContinue && !hasBranches) {
    return null;
  }

  return (
    <div className="story-actions">
      <div className="actions-header">
        <span className="actions-ornament">◈</span>
        <span className="actions-label">What happens next?</span>
        <span className="actions-ornament">◈</span>
      </div>

      <div className="actions-container">
        {/* Continue button */}
        {canContinue && (
          <button
            className="action-button action-continue"
            onClick={onContinue}
            type="button"
          >
            <span className="action-icon">▶</span>
            <span className="action-text">Continue the Story</span>
            <span className="action-arrow">→</span>
          </button>
        )}

        {/* Branch options */}
        {hasBranches && (
          <div className="action-branches">
            <p className="branches-intro">Or explore a different path...</p>
            {branches.map((branch, index) => (
              <button
                key={branch.id}
                className="action-button action-branch"
                onClick={() => onBranch?.(branch.id)}
                type="button"
                style={{ animationDelay: `${index * 0.1 + 0.2}s` }}
              >
                <span className="branch-icon">◇</span>
                <div className="branch-content">
                  <span className="branch-label">{branch.label}</span>
                  {branch.preview && (
                    <span className="branch-preview">{branch.preview}</span>
                  )}
                </div>
                <span className="action-arrow">→</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Atmospheric glow */}
      <div className="actions-glow" />
    </div>
  );
}
