/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        lider: {
          canvas: "#F8F8F8",
          surface: "#FFFFFF",
          "muted-bg": "#EDEDED",
          ink: "#1A1A1A",
          charcoal: "#222222",
          slate: "#666666",
          muted: "#757575",
          wood: "#8B5A2B",
          terracotta: "#A0522D",
          border: "#E0E0E0",
        },
      },
      fontFamily: {
        display: ["Montserrat", "Inter", "sans-serif"],
        sans: ["Inter", "Roboto", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        lider: "0 4px 20px rgba(0, 0, 0, 0.05)",
      },
      borderRadius: {
        none: "0px",
        xs: "2px",
        sm: "4px",
      },
    },
  },
  plugins: [],
};
