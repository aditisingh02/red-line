import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// Proxy API + metrics to the Redline backend.
// Override the port with REDLINE_API_PORT if :8001 is taken.
const API = `http://localhost:${process.env.REDLINE_API_PORT ?? 8001}`;

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: API, changeOrigin: true },
      "/metrics": { target: API, changeOrigin: true },
    },
  },
});
