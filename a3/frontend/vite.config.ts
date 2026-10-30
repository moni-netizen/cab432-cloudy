import { defineConfig } from "vite";
import { resolve } from "node:path";

// STUDENT CONFIGURATION: where your backend's HTTP API lives during `npm run dev`.
// Requests to /api/* are proxied here, so the browser sees ONE origin and the
// HttpOnly session cookie works without any CORS setup.
const BACKEND = "https://s4am6cpybl.execute-api.ap-southeast-2.amazonaws.com";
const ALB = "http://n12023868-a3-alb-605057516.ap-southeast-2.elb.amazonaws.com:8080";


export default defineConfig({
  server: {
    proxy: {
      "/a3": { target: BACKEND, changeOrigin: true },
      "/acp": { target: ALB, ws: true, changeOrigin: true },
    },
  },
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        dashboard: resolve(__dirname, "dashboard.html"),
        forum: resolve(__dirname, "forum.html"),
        chat: resolve(__dirname, "chat.html")
      },
    },
  },
});
