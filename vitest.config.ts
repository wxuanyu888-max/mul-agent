import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const repoRoot = path.dirname(fileURLToPath(import.meta.url));
const isCI = process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";
const localWorkers = Math.max(2, Math.min(8, os.cpus().length));
const ciWorkers = 2;

export default defineConfig({
  resolve: {
    alias: {
      "@": path.join(repoRoot, "frontend/src"),
      "@components": path.join(repoRoot, "frontend/src/components"),
      "@services": path.join(repoRoot, "frontend/src/services"),
      "@types": path.join(repoRoot, "frontend/src/types"),
      "@utils": path.join(repoRoot, "frontend/src/utils"),
    },
  },
  test: {
    testTimeout: 60_000,
    hookTimeout: 60_000,
    unstubEnvs: true,
    unstubGlobals: true,
    pool: "forks",
    maxWorkers: isCI ? ciWorkers : localWorkers,
    include: [
      "frontend/src/**/*.test.ts",
      "frontend/src/**/*.test.tsx",
      "frontend/tests/**/*.test.ts",
      "frontend/tests/**/*.test.tsx",
    ],
    exclude: [
      "frontend/node_modules/**",
      "frontend/dist/**",
      "dist/**",
      "build/**",
      ".venv/**",
      "storage/**",
      "wang/**",
      "openclaw/**",
    ],
    setupFiles: ["frontend/tests/setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      all: false,
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 55,
        statements: 70,
      },
      include: ["frontend/src/**/*.ts", "frontend/src/**/*.tsx"],
      exclude: [
        "frontend/src/**/*.test.ts",
        "frontend/src/**/*.test.tsx",
        "frontend/src/**/*.d.ts",
        "frontend/src/main.tsx",
        "frontend/src/vite-env.d.ts",
        "frontend/tests/**",
      ],
    },
  },
});
