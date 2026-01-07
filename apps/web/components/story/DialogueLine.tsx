import { useMemo } from 'react';
import './dialogue-line.css';

// Character color palette for visual distinction
const CHARACTER_COLORS: Record<string, string> = {
  // Defaults - will be overridden by world character data
  narrator: '#888888',
  default: '#00ffcc',
};

export interface DialogueLineData {
  speaker?: string;
  text: string;
  emotion?: string;
  isNarration?: boolean;
}

interface DialogueLineProps {
  line: DialogueLineData;
  characterColors?: Record<string, string>;
  showSpeaker?: boolean;
  isActive?: boolean;
  onClick?: () => void;
}

/**
 * Parse a line of text to extract speaker and dialogue
 * Supports formats:
 * - "SPEAKER: \"dialogue\"" or "SPEAKER: dialogue"
 * - "[Speaker Name] \"dialogue\"" or "[Speaker Name] dialogue"
 * - "\"dialogue\"" (no speaker, treated as continuation)
 * - Plain text (narration)
 */
export function parseDialogueLine(text: string): DialogueLineData {
  const trimmed = text.trim();

  // Pattern 1: SPEAKER_NAME: "dialogue" or SPEAKER_NAME: dialogue
  const colonMatch = trimmed.match(/^([A-Z][A-Z0-9_\s]+):\s*[""]?(.+?)[""]?$/);
  if (colonMatch) {
    return {
      speaker: colonMatch[1].trim(),
      text: colonMatch[2].trim(),
    };
  }

  // Pattern 2: [Speaker Name] "dialogue" or [Speaker Name] dialogue
  const bracketMatch = trimmed.match(/^\[([^\]]+)\]\s*[""]?(.+?)[""]?$/);
  if (bracketMatch) {
    return {
      speaker: bracketMatch[1].trim(),
      text: bracketMatch[2].trim(),
    };
  }

  // Pattern 3: Quoted text without speaker (continuation dialogue)
  const quoteMatch = trimmed.match(/^[""](.+?)[""]$/);
  if (quoteMatch) {
    return {
      text: quoteMatch[1].trim(),
    };
  }

  // Pattern 4: Plain text (narration)
  return {
    text: trimmed,
    isNarration: true,
  };
}

/**
 * Parse multiple lines/paragraphs into dialogue data
 */
export function parseDialogueContent(content: string): DialogueLineData[] {
  const paragraphs = content.split(/\n\n+/);
  return paragraphs.map(para => parseDialogueLine(para));
}

export function DialogueLine({
  line,
  characterColors = CHARACTER_COLORS,
  showSpeaker = true,
  isActive = false,
  onClick,
}: DialogueLineProps) {
  const speakerColor = useMemo(() => {
    if (!line.speaker) return characterColors.narrator || CHARACTER_COLORS.narrator;
    const key = line.speaker.toLowerCase().replace(/\s+/g, '_');
    return characterColors[key] || characterColors.default || CHARACTER_COLORS.default;
  }, [line.speaker, characterColors]);

  // Process inline formatting
  const formattedText = useMemo(() => {
    return line.text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>');
  }, [line.text]);

  if (line.isNarration) {
    return (
      <div
        className={`dialogue-line dialogue-line--narration ${isActive ? 'dialogue-line--active' : ''}`}
        onClick={onClick}
      >
        <p
          className="dialogue-line__text dialogue-line__text--narration"
          dangerouslySetInnerHTML={{ __html: formattedText }}
        />
      </div>
    );
  }

  return (
    <div
      className={`dialogue-line ${isActive ? 'dialogue-line--active' : ''}`}
      onClick={onClick}
      style={{ '--speaker-color': speakerColor } as React.CSSProperties}
    >
      {showSpeaker && line.speaker && (
        <div className="dialogue-line__speaker">
          <span className="dialogue-line__speaker-name">{line.speaker}</span>
          {line.emotion && (
            <span className="dialogue-line__emotion">({line.emotion})</span>
          )}
        </div>
      )}
      <div className="dialogue-line__content">
        <span className="dialogue-line__quote">"</span>
        <p
          className="dialogue-line__text"
          dangerouslySetInnerHTML={{ __html: formattedText }}
        />
        <span className="dialogue-line__quote">"</span>
      </div>
    </div>
  );
}

export default DialogueLine;
