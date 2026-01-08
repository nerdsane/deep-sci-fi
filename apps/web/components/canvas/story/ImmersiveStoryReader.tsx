import { useEffect, useRef, useState, useCallback } from 'react';
import { StoryHero } from './StoryHero';
import { StorySection } from './StorySection';
import { InlineMedia } from './InlineMedia';
import { WorldContext } from './WorldContext';
import { StoryActions } from './StoryActions';
import { VisualNovelReader, storyContentToVNScene } from './VisualNovelReader';
import type { CharacterSprite } from './CharacterLayer';
import './immersive.css';

// Story content types
export interface StoryContent {
  type: 'text' | 'image' | 'gallery' | 'world-context' | 'divider';
  content?: string;
  src?: string;
  images?: Array<{ src: string; alt?: string; caption?: string }>;
  contextType?: 'rule' | 'character' | 'location' | 'tech';
  title?: string;
  description?: string;
  fullBleed?: boolean;
}

// Scene configuration for VN mode
export interface SceneConfig {
  background?: string;
  music?: string;
  characters?: CharacterSprite[];
  transition?: 'fade' | 'slide' | 'dissolve';
}

export interface StoryData {
  id: string;
  title: string;
  subtitle?: string;
  heroImage?: string;
  worldName?: string;
  chapterNumber?: number;
  totalChapters?: number;
  readTime?: string;
  content: StoryContent[];
  actions?: {
    canContinue?: boolean;
    branches?: Array<{ id: string; label: string; preview?: string }>;
  };
  // VN mode settings
  scene?: SceneConfig;
  characterColors?: Record<string, string>;
}

export type ReadingMode = 'scroll' | 'visual-novel';

interface ImmersiveStoryReaderProps {
  story: StoryData;
  onContinue?: () => void;
  onBranch?: (branchId: string) => void;
  onWorldExplore?: () => void;
  /** Reading mode: 'scroll' (default) or 'visual-novel' */
  mode?: ReadingMode;
  /** Callback when mode is toggled */
  onModeChange?: (mode: ReadingMode) => void;
  /** Show mode toggle button */
  showModeToggle?: boolean;
}

export function ImmersiveStoryReader({
  story,
  onContinue,
  onBranch,
  onWorldExplore,
  mode = 'scroll',
  onModeChange,
  showModeToggle = true,
}: ImmersiveStoryReaderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [visibleSections, setVisibleSections] = useState<Set<number>>(new Set([0]));
  const [currentMode, setCurrentMode] = useState<ReadingMode>(mode);
  const [sceneBackground, setSceneBackground] = useState<string | undefined>(
    story.scene?.background || story.heroImage
  );

  // Toggle reading mode
  const toggleMode = useCallback(() => {
    const newMode = currentMode === 'scroll' ? 'visual-novel' : 'scroll';
    setCurrentMode(newMode);
    onModeChange?.(newMode);
  }, [currentMode, onModeChange]);

  // Update background when scene changes
  useEffect(() => {
    if (story.scene?.background) {
      setSceneBackground(story.scene.background);
    }
  }, [story.scene?.background]);

  // Track scroll progress for parallax effects
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleScroll = () => {
      const scrollTop = container.scrollTop;
      const scrollHeight = container.scrollHeight - container.clientHeight;
      const progress = scrollHeight > 0 ? scrollTop / scrollHeight : 0;
      setScrollProgress(progress);
    };

    container.addEventListener('scroll', handleScroll, { passive: true });
    return () => container.removeEventListener('scroll', handleScroll);
  }, []);

  // Intersection Observer for scroll-triggered animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries: IntersectionObserverEntry[]) => {
        entries.forEach((entry: IntersectionObserverEntry) => {
          const index = parseInt(entry.target.getAttribute('data-section-index') || '0', 10);
          setVisibleSections((prev) => {
            const next = new Set(prev);
            if (entry.isIntersecting) {
              next.add(index);
            }
            return next;
          });
        });
      },
      {
        root: containerRef.current,
        rootMargin: '-10% 0px -10% 0px',
        threshold: [0, 0.1, 0.5, 1]
      }
    );

    const container = containerRef.current;
    if (container) {
      const sections = container.querySelectorAll('[data-section-index]');
      sections.forEach((section: Element) => observer.observe(section));
    }

    return () => observer.disconnect();
  }, [story.content]);

  // Convert story content to VN scene format for VN mode
  const vnScene = useCallback(() => {
    // Combine all text content into dialogue lines
    const textContent = story.content
      .filter(item => item.type === 'text')
      .map(item => item.content || '')
      .join('\n\n');

    return storyContentToVNScene(
      textContent,
      story.id,
      sceneBackground,
      story.scene?.characters
    );
  }, [story.content, story.id, sceneBackground, story.scene?.characters]);

  // VN Mode rendering
  if (currentMode === 'visual-novel') {
    return (
      <div className="immersive-reader immersive-reader--vn-mode">
        {/* Mode toggle */}
        {showModeToggle && (
          <button
            className="immersive-mode-toggle"
            onClick={toggleMode}
            title="Switch to scroll mode"
          >
            <span className="mode-icon">📜</span>
            <span className="mode-label">Scroll</span>
          </button>
        )}

        <VisualNovelReader
          scene={vnScene()}
          characterColors={story.characterColors}
          choices={story.actions?.branches}
          onChoice={onBranch}
          onSceneComplete={onContinue}
        />
      </div>
    );
  }

  // Scroll Mode rendering
  return (
    <div
      ref={containerRef}
      className="immersive-reader immersive-reader--scroll-mode"
      style={{ '--scroll-progress': scrollProgress } as React.CSSProperties}
    >
      {/* Scene background layer */}
      {sceneBackground && (
        <div
          className="immersive-scene-background"
          style={{ backgroundImage: `url(${sceneBackground})` }}
        />
      )}

      {/* Atmospheric background layer */}
      <div className="immersive-atmosphere" />

      {/* Mode toggle */}
      {showModeToggle && (
        <button
          className="immersive-mode-toggle"
          onClick={toggleMode}
          title="Switch to visual novel mode"
        >
          <span className="mode-icon">🎭</span>
          <span className="mode-label">VN Mode</span>
        </button>
      )}

      {/* Progress indicator */}
      <div className="immersive-progress">
        <div
          className="immersive-progress-bar"
          style={{ transform: `scaleX(${scrollProgress})` }}
        />
      </div>

      {/* Hero section */}
      <StoryHero
        title={story.title}
        subtitle={story.subtitle}
        heroImage={story.heroImage}
        worldName={story.worldName}
        chapterInfo={
          story.chapterNumber && story.totalChapters
            ? `Chapter ${story.chapterNumber} of ${story.totalChapters}`
            : undefined
        }
        readTime={story.readTime}
        scrollProgress={scrollProgress}
        onWorldClick={onWorldExplore}
      />

      {/* Story content */}
      <div className="immersive-content">
        {story.content.map((item, index) => {
          const isVisible = visibleSections.has(index);
          const sectionProps = {
            'data-section-index': index,
            className: `immersive-section ${isVisible ? 'visible' : ''}`
          };

          switch (item.type) {
            case 'text':
              return (
                <StorySection
                  key={index}
                  {...sectionProps}
                  content={item.content || ''}
                  isVisible={isVisible}
                  index={index}
                />
              );

            case 'image':
              return (
                <InlineMedia
                  key={index}
                  {...sectionProps}
                  type="image"
                  src={item.src}
                  caption={item.description}
                  fullBleed={item.fullBleed}
                  isVisible={isVisible}
                />
              );

            case 'gallery':
              return (
                <InlineMedia
                  key={index}
                  {...sectionProps}
                  type="gallery"
                  images={item.images}
                  isVisible={isVisible}
                />
              );

            case 'world-context':
              return (
                <WorldContext
                  key={index}
                  {...sectionProps}
                  contextType={item.contextType || 'rule'}
                  title={item.title}
                  content={item.content || item.description}
                  isVisible={isVisible}
                />
              );

            case 'divider':
              return (
                <div
                  key={index}
                  {...sectionProps}
                  className={`immersive-divider ${isVisible ? 'visible' : ''}`}
                >
                  <span className="divider-ornament">✦</span>
                </div>
              );

            default:
              return null;
          }
        })}

        {/* Story actions */}
        {story.actions && (
          <StoryActions
            canContinue={story.actions.canContinue}
            branches={story.actions.branches}
            onContinue={onContinue}
            onBranch={onBranch}
          />
        )}

        {/* End flourish */}
        <div className="immersive-end">
          <div className="end-ornament">
            <span>◆</span>
            <span>◇</span>
            <span>◆</span>
          </div>
        </div>
      </div>
    </div>
  );
}
