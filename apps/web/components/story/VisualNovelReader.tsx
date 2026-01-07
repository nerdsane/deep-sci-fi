import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { DialogueLine, parseDialogueContent, type DialogueLineData } from './DialogueLine';
import { CharacterLayer, type CharacterSprite } from './CharacterLayer';
import './visual-novel.css';

export interface VNSceneData {
  id: string;
  background?: string;
  music?: string;
  characters?: CharacterSprite[];
  lines: DialogueLineData[];
}

interface VisualNovelReaderProps {
  scene: VNSceneData;
  characterColors?: Record<string, string>;
  onSceneComplete?: () => void;
  onChoice?: (choiceId: string) => void;
  choices?: Array<{ id: string; label: string; preview?: string }>;
  autoAdvance?: boolean;
  autoSpeed?: number; // ms per character
  showControls?: boolean;
}

interface VNState {
  currentLineIndex: number;
  textProgress: number; // 0-1 for typewriter
  isTyping: boolean;
  isPaused: boolean;
}

export function VisualNovelReader({
  scene,
  characterColors,
  onSceneComplete,
  onChoice,
  choices,
  autoAdvance = false,
  autoSpeed = 30,
  showControls = true,
}: VisualNovelReaderProps) {
  const [state, setState] = useState<VNState>({
    currentLineIndex: 0,
    textProgress: 0,
    isTyping: true,
    isPaused: false,
  });

  const containerRef = useRef<HTMLDivElement>(null);
  const typingIntervalRef = useRef<number | null>(null);

  const currentLine = scene.lines[state.currentLineIndex];
  const isLastLine = state.currentLineIndex >= scene.lines.length - 1;
  const hasChoices = choices && choices.length > 0 && isLastLine;

  // Typewriter effect
  useEffect(() => {
    if (!currentLine || state.isPaused) return;

    const textLength = currentLine.text.length;
    const duration = textLength * autoSpeed;

    if (state.isTyping) {
      const startTime = Date.now();

      typingIntervalRef.current = window.setInterval(() => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);

        setState(prev => ({
          ...prev,
          textProgress: progress,
          isTyping: progress < 1,
        }));

        if (progress >= 1) {
          if (typingIntervalRef.current) {
            clearInterval(typingIntervalRef.current);
          }
        }
      }, 16); // ~60fps

      return () => {
        if (typingIntervalRef.current) {
          clearInterval(typingIntervalRef.current);
        }
      };
    }
  }, [currentLine, state.currentLineIndex, state.isPaused, autoSpeed, state.isTyping]);

  // Auto-advance
  useEffect(() => {
    if (!autoAdvance || state.isTyping || state.isPaused || hasChoices) return;

    const timer = setTimeout(() => {
      advance();
    }, 1500); // Wait 1.5s after typing completes

    return () => clearTimeout(timer);
  }, [autoAdvance, state.isTyping, state.isPaused, hasChoices]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        handleClick();
      } else if (e.key === 'Escape') {
        setState(prev => ({ ...prev, isPaused: !prev.isPaused }));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state.isTyping, isLastLine, hasChoices]);

  const advance = useCallback(() => {
    if (isLastLine) {
      if (!hasChoices) {
        onSceneComplete?.();
      }
      return;
    }

    setState(prev => ({
      ...prev,
      currentLineIndex: prev.currentLineIndex + 1,
      textProgress: 0,
      isTyping: true,
    }));
  }, [isLastLine, hasChoices, onSceneComplete]);

  const handleClick = useCallback(() => {
    if (state.isTyping) {
      // Skip to end of current line
      setState(prev => ({
        ...prev,
        textProgress: 1,
        isTyping: false,
      }));
      if (typingIntervalRef.current) {
        clearInterval(typingIntervalRef.current);
      }
    } else {
      advance();
    }
  }, [state.isTyping, advance]);

  const handleChoiceSelect = useCallback((choiceId: string) => {
    onChoice?.(choiceId);
  }, [onChoice]);

  // Get visible text based on progress
  const visibleText = useMemo(() => {
    if (!currentLine) return '';
    const charCount = Math.floor(currentLine.text.length * state.textProgress);
    return currentLine.text.slice(0, charCount);
  }, [currentLine, state.textProgress]);

  // Determine which character is speaking
  const speakingCharacter = currentLine?.speaker?.toLowerCase().replace(/\s+/g, '_');

  return (
    <div
      ref={containerRef}
      className={`vn-reader ${state.isPaused ? 'vn-reader--paused' : ''}`}
      onClick={handleClick}
    >
      {/* Background Layer */}
      {scene.background && (
        <div
          className="vn-reader__background"
          style={{ backgroundImage: `url(${scene.background})` }}
        />
      )}

      {/* Background Overlay */}
      <div className="vn-reader__overlay" />

      {/* Character Layer */}
      {scene.characters && scene.characters.length > 0 && (
        <CharacterLayer
          characters={scene.characters}
          speakingCharacterId={speakingCharacter}
        />
      )}

      {/* Dialogue Box */}
      <div className="vn-reader__dialogue-box">
        {currentLine && (
          <DialogueLine
            line={{
              ...currentLine,
              text: visibleText,
            }}
            characterColors={characterColors}
            isActive={true}
          />
        )}

        {/* Advance Indicator */}
        {!state.isTyping && !hasChoices && (
          <div className="vn-reader__advance-indicator">
            <span className="vn-reader__advance-arrow">▼</span>
          </div>
        )}
      </div>

      {/* Choices */}
      {hasChoices && !state.isTyping && (
        <div className="vn-reader__choices">
          {choices.map((choice, i) => (
            <button
              key={choice.id}
              className="vn-reader__choice"
              onClick={(e) => {
                e.stopPropagation();
                handleChoiceSelect(choice.id);
              }}
              style={{ animationDelay: `${i * 0.1}s` }}
            >
              <span className="vn-reader__choice-icon">◇</span>
              <span className="vn-reader__choice-label">{choice.label}</span>
              {choice.preview && (
                <span className="vn-reader__choice-preview">{choice.preview}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Controls */}
      {showControls && (
        <div className="vn-reader__controls">
          <button
            className="vn-reader__control"
            onClick={(e) => {
              e.stopPropagation();
              setState(prev => ({ ...prev, isPaused: !prev.isPaused }));
            }}
          >
            {state.isPaused ? '▶' : '⏸'}
          </button>
          <div className="vn-reader__progress">
            {state.currentLineIndex + 1} / {scene.lines.length}
          </div>
        </div>
      )}

      {/* Pause Overlay */}
      {state.isPaused && (
        <div className="vn-reader__pause-overlay">
          <div className="vn-reader__pause-menu">
            <h2>Paused</h2>
            <button onClick={(e) => {
              e.stopPropagation();
              setState(prev => ({ ...prev, isPaused: false }));
            }}>
              Resume
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Convert story content string to VN scene format
 */
export function storyContentToVNScene(
  content: string,
  sceneId: string,
  background?: string,
  characters?: CharacterSprite[],
): VNSceneData {
  const lines = parseDialogueContent(content);
  return {
    id: sceneId,
    background,
    characters,
    lines,
  };
}

export default VisualNovelReader;
