import { useMemo } from 'react';
import './character-layer.css';

export interface CharacterSprite {
  characterId: string;
  name?: string;
  imageUrl: string;
  position: 'left' | 'center' | 'right';
  emotion?: string;
  scale?: number;
  offsetY?: number;
  flipped?: boolean;
}

interface CharacterLayerProps {
  characters: CharacterSprite[];
  speakingCharacterId?: string;
}

export function CharacterLayer({ characters, speakingCharacterId }: CharacterLayerProps) {
  // Sort characters by position for consistent layering
  const sortedCharacters = useMemo(() => {
    const positionOrder = { left: 0, center: 1, right: 2 };
    return [...characters].sort((a, b) => positionOrder[a.position] - positionOrder[b.position]);
  }, [characters]);

  return (
    <div className="character-layer">
      {sortedCharacters.map((char) => {
        const isSpeaking = speakingCharacterId === char.characterId;
        const scale = char.scale || 1;
        const offsetY = char.offsetY || 0;

        return (
          <div
            key={char.characterId}
            className={`character-sprite character-sprite--${char.position} ${
              isSpeaking ? 'character-sprite--speaking' : 'character-sprite--idle'
            } ${char.flipped ? 'character-sprite--flipped' : ''}`}
            style={{
              transform: `scale(${scale}) translateY(${offsetY}px)`,
            }}
          >
            <img
              src={char.imageUrl}
              alt={char.name || char.characterId}
              className="character-sprite__image"
              data-emotion={char.emotion}
            />
            {/* Speaking indicator glow */}
            {isSpeaking && <div className="character-sprite__glow" />}
          </div>
        );
      })}
    </div>
  );
}

/**
 * Helper to create character sprite data from world character element
 */
export function createCharacterSprite(
  characterId: string,
  position: CharacterSprite['position'],
  imageUrl: string,
  options?: Partial<CharacterSprite>,
): CharacterSprite {
  return {
    characterId,
    position,
    imageUrl,
    ...options,
  };
}

export default CharacterLayer;
