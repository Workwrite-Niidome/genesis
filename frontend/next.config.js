/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'genesis.world',
      },
      {
        protocol: 'https',
        hostname: 'genesis-pj.net',
      },
      {
        protocol: 'https',
        hostname: '*.genesis-pj.net',
      },
      {
        protocol: 'https',
        hostname: 'pbs.twimg.com',
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000') + '/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig
