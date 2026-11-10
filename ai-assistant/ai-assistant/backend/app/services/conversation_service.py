"""`conversations` 컬렉션 관리.

문서 구조:
  conversations/{id} = {
    title: str,
    messages: [{role, content, created_at}, ...],
    created_at: ISO8601, updated_at: ISO8601
  }
"""
from datetime import datetime, timezone

from firebase_admin import firestore

from app.firebase import get_db

COLLECTION = "conversations"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _col():
    return get_db().collection(COLLECTION)


def _make_title(messages: list[dict]) -> str:
    first = next((m["content"] for m in messages if m["role"] == "user"), "새 대화")
    first = " ".join(first.split())
    return first[:30] + ("…" if len(first) > 30 else "")


def _to_detail(doc) -> dict:
    d = doc.to_dict() or {}
    msgs = d.get("messages", [])
    return {
        "id": doc.id,
        "title": d.get("title", "새 대화"),
        "message_count": len(msgs),
        "created_at": d.get("created_at", ""),
        "updated_at": d.get("updated_at", ""),
        "messages": msgs,
    }


def create_conversation(messages: list[dict], title: str | None = None) -> dict:
    now = _now()
    msgs = [{**m, "created_at": m.get("created_at") or now} for m in messages]
    data = {"title": (title or "").strip() or _make_title(msgs), "messages": msgs, "created_at": now, "updated_at": now}
    ref = _col().document()
    ref.set(data)
    return {"id": ref.id, "message_count": len(msgs), **data}


def list_conversations() -> list[dict]:
    """최근 수정 순. messages 본문은 제외하고 개수만 반환."""
    docs = _col().order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
    result = []
    for doc in docs:
        item = _to_detail(doc)
        item.pop("messages")
        result.append(item)
    return result


def get_conversation(conv_id: str) -> dict | None:
    doc = _col().document(conv_id).get()
    return _to_detail(doc) if doc.exists else None


def append_messages(conv_id: str, messages: list[dict]) -> dict | None:
    ref = _col().document(conv_id)
    doc = ref.get()
    if not doc.exists:
        return None
    now = _now()
    existing = (doc.to_dict() or {}).get("messages", [])
    new_msgs = existing + [{**m, "created_at": m.get("created_at") or now} for m in messages]
    ref.update({"messages": new_msgs, "updated_at": now})
    return _to_detail(ref.get())


def delete_conversation(conv_id: str) -> bool:
    ref = _col().document(conv_id)
    if not ref.get().exists:
        return False
    ref.delete()
    return True
