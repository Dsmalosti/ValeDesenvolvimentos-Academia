/** @type {import('tailwindcss').Config} */
const defaultTheme = require("tailwindcss/defaultTheme");

module.exports = {
  content: [
    "./app/templates/**/*.html",
    "./app/blueprints/**/templates/**/*.html",
    "./app/static/js/**/*.js",
  ],
  theme: {
    extend: {
      colors: {
        // cor principal da marca: #002f52 (navy-800)
        navy: {
          50: "#eef6fc",
          100: "#d9e9f6",
          200: "#b3d2ec",
          300: "#80b0da",
          400: "#4d88c2",
          500: "#2b67a3",
          600: "#1a5087",
          700: "#0f3f6e",
          800: "#002f52",
          900: "#00233e",
          950: "#00162a",
        },
        // destaque da marca: #FFCC00 (amarelo-400)
        amarelo: {
          50: "#fffae6",
          100: "#fff3bf",
          200: "#ffe680",
          300: "#ffd933",
          400: "#ffcc00",
          500: "#e6b800",
          600: "#b38f00",
          700: "#806600",
        },
      },
      fontFamily: {
        sans: ["Montserrat", ...defaultTheme.fontFamily.sans],
        display: ["Poppins", ...defaultTheme.fontFamily.sans],
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
