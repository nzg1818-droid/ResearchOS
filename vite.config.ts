import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  base: "./",
  resolve: { preserveSymlinks: true },
  test: {
    environment: "jsdom",
    include: ["frontend/**/*.test.{ts,tsx}"],
    setupFiles: ["frontend/test-setup.ts"],
  },
});
