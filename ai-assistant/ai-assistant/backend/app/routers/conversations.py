from fastapi import APIRouter, HTTPException, status

from app.schemas import ConversationCreate, ConversationDetail, ConversationListItem, DeleteResult
from app.services import conversation_service

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.post("", response_model=ConversationDetail, status_code=status.HTTP_201_CREATED, summary="대화 저장")
def create_conversation(payload: ConversationCreate):
    msgs = [m.model_dump(exclude_none=True) for m in payload.messages]
    return conversation_service.create_conversation(msgs, payload.title)


@router.get("", response_model=list[ConversationListItem], summary="대화 목록 조회 (messages 미포함)")
def list_conversations():
    return conversation_service.list_conversations()


@router.get("/{conv_id}", response_model=ConversationDetail, summary="특정 대화 전체 messages 조회")
def get_conversation(conv_id: str):
    conv = conversation_service.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    return conv


@router.delete("/{conv_id}", response_model=DeleteResult, summary="대화 삭제")
def delete_conversation(conv_id: str):
    if not conversation_service.delete_conversation(conv_id):
        raise HTTPException(status_code=404, detail="대화를 찾을 수 없습니다.")
    return {"id": conv_id}
