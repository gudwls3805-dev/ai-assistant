"""FastAPI 엔트리포인트.  로컬 실행: uvicorn main:app --reload"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ALLOWED_ORIGIN_REGEX, ALLOWED_ORIGINS
from app.firebase import ConfigError
from app.routers import chat, conversations, data

logger = logging.getLogger("uvicorn.error")

app = FastAPI(
    title="My Data AI Assistant API",
    version="1.0.0",
    description="내 시계열 데이터를 이해하고 답하는 AI 비서 백엔드. "
    "데이터 요약을 시스템 프롬프트에 주입(컨텍스트 주입)해 GPT 답변을 생성합니다.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(data.router)
app.include_router(conversations.router)
app.include_router(chat.router)


@app.exception_handler(ConfigError)
async def config_error_handler(_: Request, exc: ConfigError):
    logger.error("설정 오류: %s", exc)
    return JSONResponse(status_code=500, content={"detail": f"서버 설정 오류: {exc}"})


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception):
    # 내부 오류 상세는 로그에만 남기고 클라이언트에는 일반 메시지만 반환
    logger.exception("처리되지 않은 오류")
    return JSONResponse(status_code=500, content={"detail": "서버 내부 오류가 발생했습니다."})


@app.get("/", tags=["health"], summary="서비스 정보")
def root():
    return {"service": "My Data AI Assistant API", "docs": "/docs", "health": "/health"}


@app.get("/health", tags=["health"], summary="헬스 체크 (콜드스타트 깨우기용)")
def health():
    return {"status": "ok"}
