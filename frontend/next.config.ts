import type { NextConfig } from "next";

/**
 * `S3_PUBLIC_HOST` lets a CDN / Cloudflare R2 domain be whitelisted for
 * next/image without editing this file.
 */
const s3PublicHost = process.env.S3_PUBLIC_HOST;

/**
 * The API host, whitelisted for `/media/**`.
 *
 * When object storage is off — which is the normal setup on shared hosting —
 * product images are served by Django itself, at
 * `https://api.example.com/media/…`. next/image refuses any host that is not
 * listed here, so without this every listing photo comes back as a 400 and
 * the catalogue looks empty. Derived from the API URL rather than asking for
 * yet another variable, since it is the same host by construction.
 *
 * Read at build time: a change requires rebuilding, not just restarting.
 */
function apiMediaPattern() {
  const raw = process.env.NEXT_PUBLIC_API_URL ?? process.env.API_URL;
  if (!raw) return [];
  try {
    const url = new URL(raw);
    return [
      {
        protocol: url.protocol.replace(":", "") as "http" | "https",
        hostname: url.hostname,
        port: url.port,
        pathname: "/media/**" as const,
      },
    ];
  } catch {
    // An unparseable URL must not break the build; the local patterns below
    // still cover development.
    return [];
  }
}

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
      ...apiMediaPattern(),
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
