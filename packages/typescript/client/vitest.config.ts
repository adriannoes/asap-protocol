import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vitest/config";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  resolve: {
    alias: {
      keytar: path.resolve(root, "test/mocks/keytar.ts"),
    },
  },
  test: {
    environment: "node",
    passWithNoTests: true,
    include: ["test/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "text-summary"],
      include: ["src/**/*.ts"],
      exclude: ["src/**/*.d.ts"],
      thresholds: {
        lines: 90,
        statements: 87,
        functions: 90,
        branches: 70,
      },
    },
  },
});
