/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        graphite: {
          950: '#07090d',
          900: '#0b0e14',
          850: '#10141c',
          800: '#151a24',
        },
      },
      boxShadow: {
        glow: '0 0 36px rgba(34, 211, 238, 0.10)',
      },
    },
  },
  plugins: [],
}
