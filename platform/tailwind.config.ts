import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    screens: {
      'xs': '375px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
    extend: {
      colors: {
        // Backgrounds - subtle depth levels
        bg: {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
          elevated: 'var(--bg-elevated)',
        },
        // Neon Accents
        neon: {
          // Primary - Neon Teal
          cyan: 'var(--neon-cyan)',
          'cyan-bright': 'var(--neon-cyan-bright)',
          'cyan-dim': 'var(--neon-cyan-dim)',
          'cyan-muted': 'var(--neon-cyan-muted)',
          // Secondary - Electric Violet
          purple: 'var(--neon-purple)',
          'purple-bright': 'var(--neon-purple-bright)',
          'purple-dim': 'var(--neon-purple-dim)',
          'purple-muted': 'var(--neon-purple-muted)',
          // Tertiary - Hot Pink (errors)
          pink: 'var(--neon-pink)',
          'pink-bright': 'var(--neon-pink-bright)',
          'pink-dim': 'var(--neon-pink-dim)',
          'pink-muted': 'var(--neon-pink-muted)',
          // Success - Mint Green
          green: 'var(--neon-green)',
          'green-bright': 'var(--neon-green-bright)',
          'green-dim': 'var(--neon-green-dim)',
          // Warning - Amber
          amber: 'var(--neon-amber)',
          'amber-bright': 'var(--neon-amber-bright)',
          'amber-dim': 'var(--neon-amber-dim)',
        },
        // Text hierarchy
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          muted: 'var(--text-muted)',
        },
        // Borders
        border: {
          subtle: 'var(--border-subtle)',
          DEFAULT: 'var(--border-default)',
          strong: 'var(--border-strong)',
        },
      },
      fontFamily: {
        mono: ['var(--font-mono)'],
        display: ['var(--font-display)'],
      },
      fontSize: {
        // Refined type scale - more elegant, less aggressive
        'display': ['clamp(1.75rem, 4vw, 2.5rem)', { lineHeight: '1.15', letterSpacing: '0.02em' }],
        'h1': ['clamp(1.25rem, 2.5vw, 1.75rem)', { lineHeight: '1.3', letterSpacing: '0.04em' }],
        'h2': ['clamp(1rem, 2vw, 1.25rem)', { lineHeight: '1.35', letterSpacing: '0.03em' }],
        'h3': ['clamp(0.875rem, 1.5vw, 1rem)', { lineHeight: '1.4', letterSpacing: '0.02em' }],
        'h4': ['clamp(0.8125rem, 1.25vw, 0.875rem)', { lineHeight: '1.4', letterSpacing: '0.02em' }],
        'body-lg': ['0.9375rem', { lineHeight: '1.7' }],
        'body': ['0.875rem', { lineHeight: '1.7' }],
        'body-sm': ['0.8125rem', { lineHeight: '1.6' }],
        'caption': ['0.6875rem', { lineHeight: '1.5', letterSpacing: '0.01em' }],
        'overline': ['0.625rem', { lineHeight: '1.5', letterSpacing: '0.12em' }],
        // Decorative card watermark titles - consistent scale
        'card-watermark': ['clamp(1.5rem, 4vw, 2rem)', { lineHeight: '1', letterSpacing: '-0.02em' }],
        'card-watermark-lg': ['clamp(2rem, 6vw, 3rem)', { lineHeight: '1', letterSpacing: '-0.02em' }],
      },
      borderRadius: {
        'none': '0',
      },
      boxShadow: {
        'neon-cyan': '0 0 15px var(--shadow-cyan)',
        'neon-cyan-lg': '0 0 25px var(--shadow-cyan), 0 0 50px var(--shadow-cyan-soft)',
        'neon-purple': '0 0 15px var(--shadow-purple)',
        'neon-purple-lg': '0 0 25px var(--shadow-purple), 0 0 50px var(--shadow-purple-soft)',
        'neon-pink': '0 0 15px var(--shadow-pink)',
        'neon-pink-lg': '0 0 25px var(--shadow-pink), 0 0 50px var(--shadow-pink-soft)',
        'elevated': '0 4px 24px rgba(0, 0, 0, 0.6)',
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
      },
      maxWidth: {
        'prose': '65ch',
        'content': '72rem',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'slide-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'scale-in': {
          '0%': { opacity: '0', transform: 'scale(0.95)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-glow': {
          '0%, 100%': { opacity: '0.5' },
          '50%': { opacity: '1' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out',
        'slide-up': 'slide-up 0.4s ease-out',
        'scale-in': 'scale-in 0.3s ease-out',
        'shimmer': 'shimmer 2s infinite linear',
        'pulse-glow': 'pulse-glow 2s infinite ease-in-out',
      },
    },
  },
  plugins: [],
}

export default config
