/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  // Transpile workspace packages
  transpilePackages: ['@deep-sci-fi/db', '@deep-sci-fi/letta', '@deep-sci-fi/types'],
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '**.amazonaws.com',
      },
      {
        protocol: 'https',
        hostname: '**.r2.dev',
      },
    ],
  },
  // Enable experimental features for better monorepo support
  experimental: {
    // Allow importing from outside the app directory
    externalDir: true,
  },
};

module.exports = nextConfig;
