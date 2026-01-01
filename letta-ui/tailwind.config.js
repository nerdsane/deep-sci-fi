/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{ts,tsx,html}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['JetBrains Mono', 'Monaco', 'Courier New', 'monospace'],
        sans: ['Inter Variable', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Warm earth tone palette - NOT generic purple/blue
        sand: {
          50: '#faf9f7',
          100: '#f5f3ef',
          200: '#e8e4dc',
          300: '#d9d3c7',
          400: '#c4baa9',
          500: '#a89d88',
          600: '#8d7f6a',
          700: '#6e6354',
          800: '#524b3f',
          900: '#3a352c',
        },
        rust: {
          50: '#fef7f4',
          100: '#fdeee6',
          200: '#fad5c1',
          300: '#f6b899',
          400: '#f09367',
          500: '#e76e3e',
          600: '#cc4f23',
          700: '#a53d1b',
          800: '#7d2f15',
          900: '#5a2210',
        },
        sage: {
          50: '#f6f7f4',
          100: '#eaede5',
          200: '#d4dac8',
          300: '#b7c2a3',
          400: '#95a47a',
          500: '#748656',
          600: '#5c6a43',
          700: '#475135',
          800: '#363d28',
          900: '#272c1d',
        },
        midnight: {
          50: '#f4f5f7',
          100: '#e6e8ec',
          200: '#c9cdd6',
          300: '#a4abb9',
          400: '#7a8496',
          500: '#5a6377',
          600: '#444d5e',
          700: '#343b49',
          800: '#252a34',
          900: '#1a1d24',
        },
      },
      animation: {
        'slide-in': 'slideIn 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-in',
      },
      keyframes: {
        slideIn: {
          '0%': { transform: 'translateY(-8px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}
