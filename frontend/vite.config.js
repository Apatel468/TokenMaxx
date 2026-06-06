import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite dev server config — React runs on http://localhost:5173
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
  },
});
