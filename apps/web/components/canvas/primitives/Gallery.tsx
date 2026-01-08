import { useState, useCallback } from 'react';
import { Image } from './Image';

export interface GalleryImage {
  src: string;
  alt?: string;
  caption?: string;
}

export interface GalleryProps {
  images: GalleryImage[];
  columns?: 2 | 3 | 4;
  gap?: 'sm' | 'md' | 'lg';
  lightbox?: boolean;
  variant?: 'grid' | 'masonry' | 'carousel';
}

export function Gallery({
  images,
  columns = 3,
  gap = 'md',
  lightbox = true,
  variant = 'grid'
}: GalleryProps) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const handleImageClick = useCallback((index: number) => {
    if (lightbox) {
      setLightboxIndex(index);
      setLightboxOpen(true);
    }
  }, [lightbox]);

  const handlePrev = useCallback(() => {
    setLightboxIndex((i) => (i > 0 ? i - 1 : images.length - 1));
  }, [images.length]);

  const handleNext = useCallback(() => {
    setLightboxIndex((i) => (i < images.length - 1 ? i + 1 : 0));
  }, [images.length]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') setLightboxOpen(false);
    if (e.key === 'ArrowLeft') handlePrev();
    if (e.key === 'ArrowRight') handleNext();
  }, [handlePrev, handleNext]);

  const gapSize = gap === 'sm' ? '8px' : gap === 'md' ? '16px' : '24px';

  if (images.length === 0) {
    return (
      <div className="dsf-gallery-empty">
        No images to display
      </div>
    );
  }

  if (variant === 'carousel') {
    return (
      <div className="dsf-gallery-carousel">
        <div className="dsf-carousel-main">
          <button
            className="dsf-carousel-nav dsf-carousel-prev"
            onClick={() => setActiveIndex((i) => (i > 0 ? i - 1 : images.length - 1))}
            aria-label="Previous"
          >
            ‹
          </button>
          <div className="dsf-carousel-image-container">
            <img
              src={images[activeIndex].src}
              alt={images[activeIndex].alt || ''}
              className="dsf-carousel-image"
              onClick={() => handleImageClick(activeIndex)}
            />
          </div>
          <button
            className="dsf-carousel-nav dsf-carousel-next"
            onClick={() => setActiveIndex((i) => (i < images.length - 1 ? i + 1 : 0))}
            aria-label="Next"
          >
            ›
          </button>
        </div>
        {images[activeIndex].caption && (
          <div className="dsf-carousel-caption">{images[activeIndex].caption}</div>
        )}
        <div className="dsf-carousel-dots">
          {images.map((_, i) => (
            <button
              key={i}
              className={`dsf-carousel-dot ${i === activeIndex ? 'active' : ''}`}
              onClick={() => setActiveIndex(i)}
              aria-label={`Go to image ${i + 1}`}
            />
          ))}
        </div>

        {/* Carousel Lightbox */}
        {lightbox && lightboxOpen && (
          <div
            className="dsf-lightbox-overlay"
            onClick={() => setLightboxOpen(false)}
            onKeyDown={handleKeyDown}
            tabIndex={0}
          >
            <button className="dsf-lightbox-close" onClick={() => setLightboxOpen(false)}>×</button>
            <button className="dsf-lightbox-nav dsf-lightbox-prev" onClick={(e) => { e.stopPropagation(); handlePrev(); }}>‹</button>
            <img
              src={images[lightboxIndex].src}
              alt={images[lightboxIndex].alt || ''}
              className="dsf-lightbox-image"
              onClick={(e) => e.stopPropagation()}
            />
            <button className="dsf-lightbox-nav dsf-lightbox-next" onClick={(e) => { e.stopPropagation(); handleNext(); }}>›</button>
            {images[lightboxIndex].caption && (
              <div className="dsf-lightbox-caption">{images[lightboxIndex].caption}</div>
            )}
            <div className="dsf-lightbox-counter">{lightboxIndex + 1} / {images.length}</div>
          </div>
        )}
      </div>
    );
  }

  // Grid or Masonry variant
  return (
    <>
      <div
        className={`dsf-gallery dsf-gallery-${variant}`}
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${columns}, 1fr)`,
          gap: gapSize
        }}
      >
        {images.map((image, index) => (
          <div
            key={index}
            className="dsf-gallery-item"
            onClick={() => handleImageClick(index)}
          >
            <img
              src={image.src}
              alt={image.alt || ''}
              className="dsf-gallery-image"
            />
            {image.caption && (
              <div className="dsf-gallery-item-caption">{image.caption}</div>
            )}
          </div>
        ))}
      </div>

      {/* Grid Lightbox */}
      {lightbox && lightboxOpen && (
        <div
          className="dsf-lightbox-overlay"
          onClick={() => setLightboxOpen(false)}
          onKeyDown={handleKeyDown}
          tabIndex={0}
        >
          <button className="dsf-lightbox-close" onClick={() => setLightboxOpen(false)}>×</button>
          <button className="dsf-lightbox-nav dsf-lightbox-prev" onClick={(e) => { e.stopPropagation(); handlePrev(); }}>‹</button>
          <img
            src={images[lightboxIndex].src}
            alt={images[lightboxIndex].alt || ''}
            className="dsf-lightbox-image"
            onClick={(e) => e.stopPropagation()}
          />
          <button className="dsf-lightbox-nav dsf-lightbox-next" onClick={(e) => { e.stopPropagation(); handleNext(); }}>›</button>
          {images[lightboxIndex].caption && (
            <div className="dsf-lightbox-caption">{images[lightboxIndex].caption}</div>
          )}
          <div className="dsf-lightbox-counter">{lightboxIndex + 1} / {images.length}</div>
        </div>
      )}
    </>
  );
}
