import Link from 'next/link';
import './landing.css';

export default function LandingPage() {
  return (
    <div className="landing-page">
      <div className="landing-container">
        <div className="landing-hero">
          <h1 className="landing-title">
            <span className="landing-title__accent">◈</span> Deep Sci-Fi
          </h1>
          <p className="landing-subtitle">
            Craft immersive science fiction worlds and stories with AI agents
          </p>
          <p className="landing-description">
            Build consistent sci-fi universes with dedicated world agents.
            Create compelling narratives with story agents that respect your world's rules.
            Experience your stories through visual novels, interactive UI, and rich multimedia.
          </p>

          <div className="landing-actions">
            <Link href="/auth/signup" className="landing-button landing-button--primary">
              Get Started
            </Link>
            <Link href="/auth/signin" className="landing-button landing-button--secondary">
              Sign In
            </Link>
          </div>
        </div>

        <div className="landing-features">
          <div className="feature-card">
            <div className="feature-card__icon">🌌</div>
            <h3 className="feature-card__title">World Building</h3>
            <p className="feature-card__description">
              Create consistent sci-fi universes with AI world agents that maintain
              internal logic and track complex rules
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">📖</div>
            <h3 className="feature-card__title">Story Creation</h3>
            <p className="feature-card__description">
              Write compelling narratives with story agents that verify consistency
              with your world's established rules
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-card__icon">🎭</div>
            <h3 className="feature-card__title">Immersive Experiences</h3>
            <p className="feature-card__description">
              Experience stories through visual novel scenes, character sprites,
              audio, and agent-driven interactive UI
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
