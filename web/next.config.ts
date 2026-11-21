import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // 42 avatars are served from the Intra CDN.
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "cdn.intra.42.fr" },
      { protocol: "https", hostname: "**.cloudfront.net" },
    ],
  },
};

export default nextConfig;
