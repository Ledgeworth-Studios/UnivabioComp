import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dev server proxies /api to the FastAPI backend (`just serve`). Doing it
// here rather than enabling CORS on the backend keeps the browser talking to a
// single origin, which is also how it will be deployed: W5-5 has FastAPI serve
// the built files, so /api is same-origin in production too.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
