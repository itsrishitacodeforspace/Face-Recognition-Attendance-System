export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        base: "#f2f5f7",
        ink: "#14222f",
        accent: "#e85d04",
        sky: "#6fa3ef",
        mint: "#63a088"
      },
      boxShadow: {
        punch: "0 16px 35px rgba(20, 34, 47, 0.16)",
      },
      fontFamily: {
        sans: ["Manrope", "ui-sans-serif", "system-ui"],
        display: ["Sora", "ui-sans-serif", "system-ui"],
      },
    },
  },
  plugins: [],
};
