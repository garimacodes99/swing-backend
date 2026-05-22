export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        terminal: {
          bg: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          text: '#94a3b8',
          highlight: '#f1f5f9',
          green: '#22c55e',
          red: '#ef4444'
        }
      }
    },
  },
  plugins: [],
};
