import type { NextConfig } from "next";

// Where the Next server forwards /api/* (the FastAPI backend). The browser only ever talks to the
// origin it loaded the page from, so a phone on the same Wi-Fi works with no CORS setup.
const API_TARGET = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_TARGET}/:path*` }];
  },
  // Let phones and laptops on the local network load dev assets and hot reload.
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*", "172.*.*.*", "*.local"],
};

export default nextConfig;
