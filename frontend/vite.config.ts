import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: "./src/test/setup.ts", css: true },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("genlayer-js")) return "genlayer-sdk";
          if (id.includes("/viem/") || id.includes("\\viem\\")) return "viem";
          if (id.includes("react") || id.includes("react-router")) return "react-vendor";
        },
      },
    },
  },
});
