import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Backgrounds
        bg: {
          primary: '#000000',
          secondary: '#0a0a0a',
          tertiary: '#0f0f0f',
        },
        // Neon Accents
        neon: {
          cyan: '#00ffcc',
          'cyan-bright': '#00ffff',
          purple: '#aa00ff',
        },
        // Text
        text: {
          primary: '#c8c8c8',
          secondary: '#8a8a8a',
          tertiary: '#5a5a5a',
        },
      },
      fontFamily: {
        mono: ['Berkeley Mono', 'SF Mono', 'JetBrains Mono', 'monospace'],
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Inter', 'sans-serif'],
      },
      borderRadius: {
        // No rounded corners - sharp aesthetic
        none: '0',
      },
      boxShadow: {
        'neon-cyan': '0 0 10px rgba(0, 255, 204, 0.5), 0 0 20px rgba(0, 255, 204, 0.3)',
        'neon-purple': '0 0 10px rgba(170, 0, 255, 0.5), 0 0 20px rgba(170, 0, 255, 0.3)',
        'neon-cyan-lg': '0 0 20px rgba(0, 255, 204, 0.6), 0 0 40px rgba(0, 255, 204, 0.4)',
      },
    },
  },
  plugins: [],
}

export default config
