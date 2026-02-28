import path from "path";

const appRoot = path.resolve(__dirname, "./");

const nextConfig = {
  turbopack: {
    // Set root to current directory to ensure local package resolution
    root: appRoot,
    // Resolve Tailwind from app root so resolution does not fail when context is parent (e.g. apps/)
    resolveAlias: {
      tailwindcss: path.join(appRoot, "node_modules/tailwindcss"),
      "@tailwindcss/postcss": path.join(appRoot, "node_modules/@tailwindcss/postcss"),
    },
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
          {
            // CSP: va.vercel-scripts.com and vitals.* are required for Vercel Analytics/Web Vitals.
            key: "Content-Security-Policy",
            value: process.env.NODE_ENV === "development"
              ? "default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline' https://va.vercel-scripts.com; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: https:; font-src 'self' data:; connect-src 'self' https://raw.githubusercontent.com https://vitals.vercel-insights.com https://vitals.vercel-analytics.com;"
              : "default-src 'self'; script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data: https:; font-src 'self' data:; connect-src 'self' https://raw.githubusercontent.com https://vitals.vercel-insights.com https://vitals.vercel-analytics.com;",
          }
        ],
      },
    ];
  },
};

export default nextConfig;
