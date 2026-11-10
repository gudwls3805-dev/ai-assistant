// Vercel 빌드 스크립트: 정적 파일을 dist/ 로 복사하고,
// 환경 변수 API_BASE_URL 로 config.js 를 생성한다. (프레임워크/번들러 없음)
const fs = require("fs");
const path = require("path");

const OUT = path.join(__dirname, "dist");
const FILES = ["index.html", "style.css", "app.js"];
const apiBase = (process.env.API_BASE_URL || "").trim().replace(/\/+$/, "");

if (!apiBase) {
  console.warn("[build] API_BASE_URL 환경 변수가 없습니다. 기본값 http://localhost:8000 을 사용합니다.");
}

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });
for (const f of FILES) fs.copyFileSync(path.join(__dirname, f), path.join(OUT, f));

fs.writeFileSync(
  path.join(OUT, "config.js"),
  `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: apiBase || "http://localhost:8000" })};\n`,
);
console.log(`[build] dist/ 생성 완료 (API_BASE_URL=${apiBase || "http://localhost:8000"})`);
