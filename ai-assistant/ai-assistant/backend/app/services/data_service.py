"""`data` 컬렉션 CRUD + 요약."""
from firebase_admin import firestore

from app.firebase import get_db
from app.schemas import DataCreate, DataUpdate
from app.services.analysis import build_summary

COLLECTION = "data"


def _col():
    return get_db().collection(COLLECTION)


def _to_item(doc) -> dict:
    d = doc.to_dict() or {}
    return {"id": doc.id, "date": d.get("date", ""), "value": float(d.get("value", 0)), "memo": d.get("memo", "")}


def list_data() -> list[dict]:
    """날짜 오름차순."""
    return [_to_item(doc) for doc in _col().order_by("date").stream()]


def create_data(payload: DataCreate) -> dict:
    ref = _col().document()
    record = {"date": payload.date.isoformat(), "value": payload.value, "memo": payload.memo}
    ref.set({**record, "created_at": firestore.SERVER_TIMESTAMP})
    return {"id": ref.id, **record}


def update_data(item_id: str, payload: DataUpdate) -> dict | None:
    ref = _col().document(item_id)
    if not ref.get().exists:
        return None
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise ValueError("수정할 필드가 없습니다.")
    if "date" in updates:
        updates["date"] = updates["date"].isoformat()
    ref.update({**updates, "updated_at": firestore.SERVER_TIMESTAMP})
    return _to_item(ref.get())


def delete_data(item_id: str) -> bool:
    ref = _col().document(item_id)
    if not ref.get().exists:
        return False
    ref.delete()
    return True


def get_summary() -> dict:
    return build_summary(list_data())
