import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base must match the GitHub repo name so assets load from /SaarthiX-DocBuddy/
export default defineConfig({
  plugins: [react()],
  base: "/SaarthiX-DocBuddy/",
  server: { port: 5173 },
});
