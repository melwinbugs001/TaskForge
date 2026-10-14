/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        forge: {
          950: "#f5f7fb",
          900: "#ffffff",
          800: "#e8ebf8",
          700: "#d5d9ef",
          500: "#635bdb",
          400: "#5148c8",
          300: "#453da8"
        }
      },
      boxShadow: {
        glow: "0 8px 20px rgba(99, 91, 219, 0.2)"
      }
    }
  },
  plugins: []
};
