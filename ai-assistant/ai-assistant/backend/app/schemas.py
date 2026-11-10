"""Pydantic 스키마: 요청 검증 + 응답 형태 정의 (Swagger 문서에도 그대로 노출됨)."""
from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

MAX_VALUE = 1_000_000_000_000  # 비정상적으로 큰 값 차단


# ---------- data ----------
class DataCreate(BaseModel):
    date: Date = Field(..., description="날짜 (YYYY-MM-DD)", examples=["2026-10-29"])
    value: float = Field(..., ge=0, le=MAX_VALUE, description="값 (0 이상)", examples=[250000])
    memo: str = Field("", max_length=200, description="메모 (최대 200자)", examples=["할인 행사"])

    @field_validator("memo")
    @classmethod
    def strip_memo(cls, v: str) -> str:
        return v.strip()


class DataUpdate(BaseModel):
    """부분 수정: 보낸 필드만 변경된다."""
    date: Optional[Date] = None
    value: Optional[float] = Field(None, ge=0, le=MAX_VALUE)
    memo: Optional[str] = Field(None, max_length=200)

    @field_validator("memo")
    @classmethod
    def strip_memo(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v is not None else v


class DataItem(BaseModel):
    id: str
    date: str
    value: float
    memo: str = ""


class Metrics(BaseModel):
    total: float
    average: float
    max: float
    max_date: str
    min: float
    min_date: str
    std: float


class MonthlyStat(BaseModel):
    month: str
    count: int
    total: float
    average: float


class LatestMonth(MonthlyStat):
    vs_overall_daily_avg_pct: Optional[float] = None


class Summary(BaseModel):
    period: str
    count: int
    metrics: Optional[Metrics]
    trend: str
    trend_change_pct: Optional[float]
    recent_7_days_average: Optional[float]
    latest_month: Optional[LatestMonth]
    monthly: list[MonthlyStat]


# ---------- conversations ----------
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=8000)
    created_at: Optional[str] = None


class ConversationCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=100)
    messages: list[Message] = Field(..., min_length=1)


class ConversationListItem(BaseModel):
    """목록 응답에는 messages를 포함하지 않는다 (상세는 GET /api/conversations/{id})."""
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetail(ConversationListItem):
    messages: list[Message]


# ---------- chat ----------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, examples=["이번 달 실적이 어때?"])
    conversation_id: Optional[str] = Field(None, description="이어서 대화할 대화 ID (없으면 새 대화)")

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("메시지가 비어 있습니다.")
        return v


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str
    title: str


class DeleteResult(BaseModel):
    id: str
    deleted: bool = True
