import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev server config — React runs on http://localhost:5173
// For GitHub Pages (https://apatel468.github.io/TokenMaxx/), build with:
//   VITE_BASE=/TokenMaxx/ npm run build
export default defineConfig({
  base: process.env.VITE_BASE || "/",
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
  },
});
