import path from "path";

const nextConfig = {
  turbopack: {
    // Set root to current directory to ensure local package resolution
    root: path.resolve(__dirname, "./"),
  },
};

export default nextConfig;
