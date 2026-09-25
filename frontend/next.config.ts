import type { NextConfig } from "next";

/**
 * `S3_PUBLIC_HOST` lets the production media domain (Cloudflare R2 / CDN)
 * be whitelisted for next/image without a rebuild of this file.
 */
const s3PublicHost = process.env.S3_PUBLIC_HOST;

const nextConfig: NextConfig = {
  // Produces .next/standalone, which the Docker runtime image ships.
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/media/**" },
      { protocol: "http", hostname: "127.0.0.1", port: "8000", pathname: "/media/**" },
      // Backend container in docker compose.
      { protocol: "http", hostname: "backend", port: "8000", pathname: "/media/**" },
      // Local MinIO bucket.
      { protocol: "http", hostname: "minio", port: "9000", pathname: "/**" },
      { protocol: "http", hostname: "127.0.0.1", port: "9000", pathname: "/**" },
      ...(s3PublicHost
        ? [{ protocol: "https" as const, hostname: s3PublicHost, pathname: "/**" }]
        : []),
    ],
    // Dev and docker-compose serve media from loopback/private addresses;
    // in production the media host is public, so this is a no-op there.
    dangerouslyAllowLocalIP: true,
  },
};

export default nextConfig;
