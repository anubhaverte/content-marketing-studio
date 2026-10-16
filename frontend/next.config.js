/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Card Studio connects to backend at http://localhost:8000
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
};

module.exports = nextConfig;
