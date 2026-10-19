/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Card Studio connects to backend at http://localhost:8000 locally or /api on Vercel
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.VERCEL ? "/api" : "http://localhost:8000"),
  },
};

module.exports = nextConfig;
