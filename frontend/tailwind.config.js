/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        redops: {
          900: '#1a0505',
          800: '#3a0c0c',
          700: '#6a1414',
          600: '#9b1b1b',
          500: '#cc2222',
          400: '#e04a4a',
          300: '#ed7c7c',
          100: '#ffe5e5',
          50: '#fff0f0'
        }
      }
    },
  },
  plugins: [],
}
