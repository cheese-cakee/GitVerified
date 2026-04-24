import type { NextConfig } from "next";

/**
 * next.config.ts — previously empty, which meant:
 *
 * 1. NEXT_PUBLIC_API_URL (defined in .env.example) was never forwarded to
 *    the browser bundle.
 * 2. There was no dev-time proxy, so fetch('/api/...') calls in the
 *    frontend would hit the Next.js 404 handler instead of the Python
 *    backend on :3001 — unless every route had its own proxy handler.
 *
 * Changes:
 * - `rewrites()` proxies /api/:path* → http://localhost:3001/api/:path*
 *   as a fallback (after Next.js API route files).  This means any route
 *   not covered by an app/api/** file is transparently forwarded to the
 *   Python backend.  The leaderboard, status, and evaluate routes that
 *   have explicit Next.js handlers continue to work unchanged.
 * - `env` block re-exposes NEXT_PUBLIC_API_URL so code that needs the
 *   raw backend URL (e.g. server-side fetch in route handlers) can read
 *   it via process.env.NEXT_PUBLIC_API_URL with a safe localhost default.
 */
const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001",
  },

  async rewrites() {
    return {
      // Fallback rewrites run AFTER all Next.js pages and API routes.
      // Only requests that didn't match an app/api/** file reach here.
      fallback: [
        {
          source: "/api/:path*",
          destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001"}/api/:path*`,
        },
      ],
    };
  },
};

export default nextConfig;
