import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@asap-protocol/client", "@asap-protocol/mastra"],
};

export default nextConfig;
