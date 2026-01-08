import { useMemo } from 'react';

interface StorySectionProps {
  content: string;
  isVisible: boolean;
  index: number;
  'data-section-index'?: number;
  className?: string;
}

export function StorySection({
  content,
  isVisible,
  index,
  ...props
}: StorySectionProps) {
  // Parse content for special formatting
  // Supports: **bold**, *italic*, "dialogue", ---breaks---
  const formattedContent = useMemo(() => {
    // Split into paragraphs
    const paragraphs = content.split(/\n\n+/);

    return paragraphs.map((para, pIndex) => {
      // Check for special paragraph types
      const trimmed = para.trim();

      // Scene break
      if (trimmed === '---' || trimmed === '***') {
        return (
          <div key={pIndex} className="story-scene-break">
            <span>⊹</span>
            <span>⊹</span>
            <span>⊹</span>
          </div>
        );
      }

      // Dialogue detection (starts with quote)
      const isDialogue = trimmed.startsWith('"') || trimmed.startsWith('"');

      // Process inline formatting
      let processed = trimmed
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Styled quotes
        .replace(/"([^"]+)"/g, '<span class="dialogue">"$1"</span>')
        .replace(/"([^"]+)"/g, '<span class="dialogue">"$1"</span>');

      return (
        <p
          key={pIndex}
          className={`story-paragraph ${isDialogue ? 'dialogue-para' : ''}`}
          style={{
            animationDelay: `${pIndex * 0.1}s`
          }}
          dangerouslySetInnerHTML={{ __html: processed }}
        />
      );
    });
  }, [content]);

  // Stagger delay based on section index
  const staggerDelay = index * 0.05;

  return (
    <div
      {...props}
      className={`story-section ${isVisible ? 'visible' : ''}`}
      style={{
        '--stagger-delay': `${staggerDelay}s`
      } as React.CSSProperties}
    >
      <div className="section-content">
        {formattedContent}
      </div>
    </div>
  );
}
