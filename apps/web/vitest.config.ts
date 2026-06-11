import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: [],
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
      "@fbgroup/api-client": resolve(
        __dirname,
        "../../packages/api-client/src/index.ts"
      ),
      "@fbgroup/i18n": resolve(__dirname, "../../packages/i18n/src/index.tsx"),
    },
  },
});
