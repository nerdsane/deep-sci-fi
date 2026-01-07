'use client';

interface MessageActionProps {
  action: 'created_element' | 'updated_world' | 'generated_image' | 'checked_consistency' | 'created_vn_scene';
  data: any;
}

export function MessageAction({ action, data }: MessageActionProps) {
  switch (action) {
    case 'created_element':
      return (
        <div className="message-action message-action--created">
          <div className="message-action__icon">✨</div>
          <div className="message-action__body">
            <strong>Created Element</strong>
            <p>
              {data.elementType}: {data.elementName}
            </p>
            <button
              className="message-action__button"
              onClick={() => {
                // Navigate to element
                console.log('View element:', data.elementId);
              }}
            >
              View →
            </button>
          </div>
        </div>
      );

    case 'generated_image':
      return (
        <div className="message-action message-action--image">
          <div className="message-action__icon">🎨</div>
          <div className="message-action__body">
            <strong>Generated Image</strong>
            <img
              src={data.imageUrl}
              alt={data.description}
              className="message-action__image"
              loading="lazy"
            />
            <p className="message-action__prompt">{data.prompt}</p>
          </div>
        </div>
      );

    case 'checked_consistency':
      return (
        <div className="message-action message-action--check">
          <div className="message-action__icon">
            {data.consistent ? '✅' : '⚠️'}
          </div>
          <div className="message-action__body">
            <strong>Consistency Check</strong>
            <p>
              {data.consistent
                ? 'No contradictions found'
                : `Found ${data.contradictions?.length || 0} issues`}
            </p>
            {!data.consistent && data.contradictions && (
              <ul className="message-action__list">
                {data.contradictions.map((c: any, i: number) => (
                  <li key={i}>{c.description}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      );

    case 'created_vn_scene':
      return (
        <div className="message-action message-action--vn">
          <div className="message-action__icon">🎭</div>
          <div className="message-action__body">
            <strong>Created Visual Novel Scene</strong>
            <p>
              {data.characterCount} characters, {data.lineCount} dialogue lines
            </p>
            {data.background && (
              <img
                src={data.background}
                alt="Scene background"
                className="message-action__thumbnail"
                loading="lazy"
              />
            )}
            <button className="message-action__button">View Scene →</button>
          </div>
        </div>
      );

    default:
      return null;
  }
}
