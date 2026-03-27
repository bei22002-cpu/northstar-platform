import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/auth": "http://localhost:8000",
      "/leads": "http://localhost:8000",
      "/outreach": "http://localhost:8000",
      "/health": "http://localhost:8000",
      "/ai-engines": "http://localhost:8000",
      "/funding": "http://localhost:8000",
      "/research": "http://localhost:8000",
      "/business-ideas": "http://localhost:8000",
      "/rewards": "http://localhost:8000",
      "/agent": "http://localhost:8000",
    },
  },
});
