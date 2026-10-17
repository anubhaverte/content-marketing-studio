/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: "#232324",
        nav: "#0E0E10",
        panel: "#1E1E20",
        recessed: "#181818",
        muted: "#696970",
        secondary: "#A1A1AA",
        supporting: "#EBECED",
        divider: "#38383C",
      },
    },
  },
  plugins: [],
};
