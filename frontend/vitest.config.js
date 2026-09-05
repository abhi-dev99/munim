import { defineConfig } from "vitest/config";

// Minimal config: we only unit-test pure logic (see src/app/utils/*.test.js),
// so a plain node environment is enough — no jsdom/browser shim needed.
export default defineConfig({
  test: {
    environment: "node",
  },
});
