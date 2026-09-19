import { defineConfig } from "vitest/config";

// Minimal config: the only tests today are pure-function unit tests (image
// quality analysis) that need no DOM/canvas, so the plain "node" test
// environment is enough — no jsdom or React plugin required.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.js"],
  },
});
