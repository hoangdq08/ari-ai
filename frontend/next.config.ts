import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    const backendInternalUrl = process.env.BACKEND_INTERNAL_URL || "http://127.0.0.1:8081";

    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendInternalUrl}/api/v1/:path*`,
      },
    ];
  },
  output: "standalone",
};

export default nextConfig;
