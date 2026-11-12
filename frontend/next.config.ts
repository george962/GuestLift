import type {NextConfig} from 'next';
const nextConfig:NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // Enable for Cloudflare Pages or any static CDN. Docker retains SSR by default.
  ...(process.env.GUESTLIFT_STATIC_EXPORT==='1'?{output:'export' as const}:{}),
};
export default nextConfig;
