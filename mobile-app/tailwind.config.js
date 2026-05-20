/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: {
          darkest: '#020617', // slate-950
          dark: '#0f172a',    // slate-900
        },
        emergency: {
          DEFAULT: '#ef4444', // red-500
          light: '#fca5a5',
        },
        success: {
          DEFAULT: '#10b981', // emerald-500
          light: '#a7f3d0',
        },
        alert: {
          DEFAULT: '#f59e0b', // amber-500
          light: '#fde68a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
