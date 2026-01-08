import { useState } from 'react';

interface ImageData {
  src: string;
  alt?: string;
  caption?: string;
}

interface InlineMediaProps {
  type: 'image' | 'gallery';
  src?: string;
  caption?: string;
  images?: ImageData[];
  fullBleed?: boolean;
  isVisible: boolean;
  'data-section-index'?: number;
  className?: string;
}

export function InlineMedia({
  type,
  src,
  caption,
  images,
  fullBleed = false,
  isVisible,
  ...props
}: InlineMediaProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState(0);

  const openLightbox = (index: number = 0) => {
    setLightboxIndex(index);
    setLightboxOpen(true);
  };

  const closeLightbox = () => setLightboxOpen(false);

  const navigateLightbox = (direction: 'prev' | 'next') => {
    if (!images) return;
    const max = images.length - 1;
    if (direction === 'prev') {
      setLightboxIndex((i) => (i === 0 ? max : i - 1));
    } else {
      setLightboxIndex((i) => (i === max ? 0 : i + 1));
    }
  };

  if (type === 'image' && src) {
    return (
      <>
        <figure
          {...props}
          className={`inline-media inline-image ${fullBleed ? 'full-bleed' : ''} ${isVisible ? 'visible' : ''}`}
        >
          <div className="media-frame">
            <img
              src={src}
              alt={caption || ''}
              onClick={() => openLightbox()}
              loading="lazy"
            />
            <div className="media-shine" />
          </div>
          {caption && <figcaption className="media-caption">{caption}</figcaption>}
        </figure>

        {/* Lightbox */}
        {lightboxOpen && (
          <div className="media-lightbox" onClick={closeLightbox}>
            <button className="lightbox-close" onClick={closeLightbox}>×</button>
            <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
              <img src={src} alt={caption || ''} />
              {caption && <p className="lightbox-caption">{caption}</p>}
            </div>
          </div>
        )}
      </>
    );
  }

  if (type === 'gallery' && images && images.length > 0) {
    return (
      <>
        <div
          {...props}
          className={`inline-media inline-gallery ${isVisible ? 'visible' : ''}`}
        >
          <div className="gallery-grid" style={{ '--count': images.length } as React.CSSProperties}>
            {images.map((img, index) => (
              <figure
                key={index}
                className="gallery-item"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="media-frame">
                  <img
                    src={img.src}
                    alt={img.alt || ''}
                    onClick={() => openLightbox(index)}
                    loading="lazy"
                  />
                  <div className="media-shine" />
                </div>
                {img.caption && <figcaption className="media-caption">{img.caption}</figcaption>}
              </figure>
            ))}
          </div>
        </div>

        {/* Lightbox with navigation */}
        {lightboxOpen && images && images.length > 0 && (
          <div className="media-lightbox" onClick={closeLightbox}>
            <button className="lightbox-close" onClick={closeLightbox}>×</button>
            {images.length > 1 && (
              <>
                <button
                  className="lightbox-nav lightbox-prev"
                  onClick={(e) => { e.stopPropagation(); navigateLightbox('prev'); }}
                >
                  ‹
                </button>
                <button
                  className="lightbox-nav lightbox-next"
                  onClick={(e) => { e.stopPropagation(); navigateLightbox('next'); }}
                >
                  ›
                </button>
              </>
            )}
            <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
              <img src={images[lightboxIndex]?.src || ''} alt={images[lightboxIndex]?.alt || ''} />
              {images[lightboxIndex]?.caption && (
                <p className="lightbox-caption">{images[lightboxIndex].caption}</p>
              )}
              {images.length > 1 && (
                <p className="lightbox-counter">
                  {lightboxIndex + 1} / {images.length}
                </p>
              )}
            </div>
          </div>
        )}
      </>
    );
  }

  return null;
}
