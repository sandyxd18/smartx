import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The browser only talks to the Vite server; /api is proxied to the FastAPI backend.
const apiUrl = process.env.SMARTX_API_URL ?? "http://127.0.0.1:8000";
const port = Number(process.env.SMARTX_PORT ?? 8080);
const host = process.env.SMARTX_BIND ?? "127.0.0.1";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host,
    port,
    strictPort: true,
    proxy: {
      "/api": { target: apiUrl, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
  },
});
