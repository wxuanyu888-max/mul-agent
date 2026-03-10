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
      "@": path.join(repoRoot, "ui/src"),
      "@components": path.join(repoRoot, "ui/src/components"),
      "@services": path.join(repoRoot, "ui/src/services"),
      "@types": path.join(repoRoot, "ui/src/types"),
      "@utils": path.join(repoRoot, "ui/src/utils"),
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
      "ui/src/**/*.test.ts",
      "ui/src/**/*.test.tsx",
      "ui/tests/**/*.test.ts",
      "ui/tests/**/*.test.tsx",
    ],
    exclude: [
      "ui/node_modules/**",
      "ui/dist/**",
      "dist/**",
      "build/**",
      ".venv/**",
      "storage/**",
      "wang/**",
      "openclaw/**",
    ],
    setupFiles: ["ui/tests/setup.ts"],
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
      include: ["ui/src/**/*.ts", "ui/src/**/*.tsx"],
      exclude: [
        "ui/src/**/*.test.ts",
        "ui/src/**/*.test.tsx",
        "ui/src/**/*.d.ts",
        "ui/src/main.tsx",
        "ui/src/vite-env.d.ts",
        "ui/tests/**",
      ],
    },
  },
});
