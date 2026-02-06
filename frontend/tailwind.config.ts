import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Background - deep space black with subtle blue
        'bg-primary': '#0a0a0f',
        'bg-secondary': '#12121a',
        'bg-tertiary': '#1a1a25',
        'bg-hover': '#22222f',

        // Accent - divine gold
        'accent-gold': '#ffc300',
        'accent-gold-dim': '#b38600',
        'accent-gold-glow': 'rgba(255, 195, 0, 0.2)',

        // Text
        'text-primary': '#e0e0e0',
        'text-secondary': '#8888a0',
        'text-muted': '#555566',

        // God/Special
        'god-glow': '#ffd700',
        'blessing': '#ffe066',

        // Karma
        'karma-up': '#4caf50',
        'karma-down': '#f44336',

        // Submolt colors
        'submolt-general': '#6366f1',
        'submolt-creations': '#ec4899',
        'submolt-election': '#f59e0b',
        'submolt-thoughts': '#8b5cf6',
        'submolt-questions': '#14b8a6',
        'submolt-gods': '#ffd700',
        'submolt-announcements': '#ef4444',

        // Border
        'border-default': '#2a2a3a',
        'border-hover': '#3a3a4a',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'god-glow': '0 0 20px rgba(255, 215, 0, 0.3)',
        'card': '0 2px 8px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.4)',
      },
      animation: {
        'glow-pulse': 'glow-pulse 2s ease-in-out infinite',
      },
      keyframes: {
        'glow-pulse': {
          '0%, 100%': { boxShadow: '0 0 20px rgba(255, 215, 0, 0.3)' },
          '50%': { boxShadow: '0 0 30px rgba(255, 215, 0, 0.5)' },
        },
      },
    },
  },
  plugins: [],
}
export default config
