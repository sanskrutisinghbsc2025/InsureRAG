/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        saas: {
          bg: '#f4f7f6',
          card: '#ffffff',
          border: '#e2e8f0',
          text: '#0f172a',
          primary: '#2563eb'
        }
      }
    },
  },
  plugins: [],
}
