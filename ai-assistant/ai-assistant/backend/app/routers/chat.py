from fastapi import APIRouter, HTTPException

from app.schemas import ChatRequest, ChatResponse
from app.services import chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, summary="AI 채팅 (데이터 요약 컨텍스트 주입 + 자동 저장)")
def chat(payload: ChatRequest):
    try:
        return chat_service.chat(payload.message, payload.conversation_id)
    except chat_service.ChatError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
