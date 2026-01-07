import { useState, useCallback } from 'react';

export interface ImageProps {
  src: string;
  alt?: string;
  caption?: string;
  size?: 'small' | 'medium' | 'large' | 'full';
  lightbox?: boolean;
  onClick?: () => void;
}

export function Image({
  src,
  alt = '',
  caption,
  size = 'medium',
  lightbox = true,
  onClick
}: ImageProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const handleClick = useCallback(() => {
    if (onClick) {
      onClick();
    } else if (lightbox) {
      setIsOpen(true);
    }
  }, [onClick, lightbox]);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setIsOpen(false);
    }
  }, []);

  const sizeClass = `dsf-image-${size}`;

  if (hasError) {
    return (
      <div className="dsf-image-error">
        <span className="dsf-image-error-icon">⚠</span>
        <span>Failed to load image</span>
      </div>
    );
  }

  return (
    <>
      <figure className={`dsf-image-figure ${sizeClass}`}>
        <div className="dsf-image-container">
          {!isLoaded && <div className="dsf-image-skeleton" />}
          <img
            src={src}
            alt={alt}
            className={`dsf-image ${isLoaded ? 'loaded' : 'loading'}`}
            onClick={handleClick}
            onLoad={() => setIsLoaded(true)}
            onError={() => setHasError(true)}
            style={{ cursor: lightbox ? 'zoom-in' : onClick ? 'pointer' : 'default' }}
          />
        </div>
        {caption && <figcaption className="dsf-image-caption">{caption}</figcaption>}
      </figure>

      {/* Lightbox */}
      {lightbox && isOpen && (
        <div
          className="dsf-lightbox-overlay"
          onClick={handleClose}
          onKeyDown={handleKeyDown}
          tabIndex={0}
          role="dialog"
          aria-modal="true"
        >
          <button className="dsf-lightbox-close" onClick={handleClose} aria-label="Close">
            ×
          </button>
          <img
            src={src}
            alt={alt}
            className="dsf-lightbox-image"
            onClick={(e) => e.stopPropagation()}
          />
          {caption && <div className="dsf-lightbox-caption">{caption}</div>}
        </div>
      )}
    </>
  );
}
