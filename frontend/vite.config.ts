import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 개발: npm run dev (5173) → /api 는 FastAPI(8000)로 넘긴다.
// 배포: npm run build → dist/ 를 FastAPI 가 / 에서 그대로 서빙한다.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000", "/health": "http://127.0.0.1:8000" } },
});
