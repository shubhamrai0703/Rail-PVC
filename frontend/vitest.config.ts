import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

/**
 * Mirrors the `@/*` path alias from tsconfig.json.
 *
 * Without it, any test that imports a component using `@/…` fails to resolve —
 * which is why the suite had, until now, only covered modules that stick to
 * relative imports. Nothing else about the default vitest behaviour changes.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
});
