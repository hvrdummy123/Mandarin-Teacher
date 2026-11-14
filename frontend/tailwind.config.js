/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper: "#F6F1E7",
        ink: "#1F1B16",
        vermilion: "#C8372D",
        jade: "#3F7D6B",
        muted: "#8A8173",
        charcoal: "#1A1816",
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        hanzi: "1.375rem",
      },
    },
  },
  plugins: [],
};
