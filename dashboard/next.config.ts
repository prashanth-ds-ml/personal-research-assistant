import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Lets a second dev server write somewhere else, so trying changes never touches the build the live servers use.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
