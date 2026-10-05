import type { NextConfig } from "next";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  devIndicators: false,
  output: "standalone", // small self-contained server for Docker
  poweredByHeader: false,

  // Proxy /api/* to the FastAPI backend, so the browser never needs CORS.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_URL}/api/:path*` }];
  },

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // This app uses the microphone, camera and location, and nothing else.
          { key: "Permissions-Policy", value: "microphone=(self), camera=(self), geolocation=(self), payment=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
