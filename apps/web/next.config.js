/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@deep-sci-fi/db', '@deep-sci-fi/types'],
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
};

module.exports = nextConfig;
