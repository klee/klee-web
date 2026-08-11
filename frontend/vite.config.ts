/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const kleeVersion = process.env.KLEE_VERSION ?? (mode === "test" ? "v3.2-test" : undefined);

  if (!kleeVersion) {
    throw new Error("KLEE_VERSION is required");
  }
  return {
    define: {
      KLEE_VERSION: JSON.stringify(kleeVersion),
    },
    plugins: [react(), tailwindcss()],
    server: {
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
    test: {
      environment: "node",
      include: ["src/**/*.test.ts"],
    },
  };
});
