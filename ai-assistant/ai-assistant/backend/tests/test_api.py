"""Firestore/OpenAI를 가짜 객체로 대체해 API 전체 흐름을 검증한다.

실행: python -m pytest -q   (backend 폴더에서)
"""
import uuid

import pytest
from fastapi.testclient import TestClient


# ---------- 인메모리 Firestore 대역 ----------
class _Snap:
    def __init__(self, ref, data):
        self.reference, self.id, self._data = ref, ref.id, data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _Doc:
    def __init__(self, store, doc_id):
        self.store, self.id = store, doc_id

    def set(self, data):
        self.store[self.id] = {k: v for k, v in data.items() if not _is_sentinel(v)}

    def get(self):
        return _Snap(self, self.store.get(self.id))

    def update(self, data):
        self.store[self.id].update({k: v for k, v in data.items() if not _is_sentinel(v)})

    def delete(self):
        self.store.pop(self.id, None)


def _is_sentinel(v):
    return type(v).__name__ == "Sentinel"


class _Col:
    def __init__(self, store, order=None, desc=False):
        self.store, self._order, self._desc = store, order, desc

    def document(self, doc_id=None):
        return _Doc(self.store, doc_id or uuid.uuid4().hex[:20])

    def order_by(self, field, direction=None):
        return _Col(self.store, field, str(direction).upper().endswith("DESCENDING"))

    def stream(self):
        docs = [_Snap(_Doc(self.store, k), v) for k, v in self.store.items()]
        if self._order:
            docs.sort(key=lambda s: s.to_dict().get(self._order, ""), reverse=self._desc)
        return iter(docs)


class FakeDB:
    def __init__(self):
        self.cols = {}

    def collection(self, name):
        return _Col(self.cols.setdefault(name, {}))


@pytest.fixture()
def client(monkeypatch):
    from app.services import chat_service, conversation_service, data_service

    db = FakeDB()
    monkeypatch.setattr(data_service, "get_db", lambda: db)
    monkeypatch.setattr(conversation_service, "get_db", lambda: db)
    captured = {}

    def fake_gpt(messages):
        captured["messages"] = messages
        return "테스트 답변입니다."

    monkeypatch.setattr(chat_service, "_call_gpt", fake_gpt)
    from main import app

    c = TestClient(app)
    c.captured = captured
    return c


def test_data_crud_and_summary(client):
    for i, v in enumerate([100, 200, 300, 400, 500, 600, 700, 800]):
        r = client.post("/api/data", json={"date": f"2026-10-0{i + 1}", "value": v, "memo": " m "})
        assert r.status_code == 201
    items = client.get("/api/data").json()
    assert len(items) == 8 and items[0]["memo"] == "m"

    s = client.get("/api/data/summary").json()
    assert s["count"] == 8 and s["metrics"]["max"] == 800 and s["trend"].startswith("상승")

    item_id = items[0]["id"]
    r = client.put(f"/api/data/{item_id}", json={"value": 999})
    assert r.status_code == 200 and r.json()["value"] == 999 and r.json()["date"] == "2026-10-01"
    assert client.put(f"/api/data/{item_id}", json={}).status_code == 400
    assert client.put("/api/data/nope", json={"value": 1}).status_code == 404

    assert client.delete(f"/api/data/{item_id}").status_code == 200
    assert client.delete(f"/api/data/{item_id}").status_code == 404
    assert len(client.get("/api/data").json()) == 7


def test_validation(client):
    assert client.post("/api/data", json={"date": "2026-13-40", "value": 1}).status_code == 422
    assert client.post("/api/data", json={"date": "2026-10-01", "value": -5}).status_code == 422
    assert client.post("/api/data", json={"date": "2026-10-01", "value": 1, "memo": "x" * 201}).status_code == 422
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422


def test_empty_summary(client):
    s = client.get("/api/data/summary").json()
    assert s["count"] == 0 and s["metrics"] is None


def test_chat_context_injection_and_autosave(client):
    client.post("/api/data", json={"date": "2026-10-01", "value": 123456})
    r = client.post("/api/chat", json={"message": "이번 달 실적이 어때?"})
    assert r.status_code == 200
    body = r.json()
    system = client.captured["messages"][0]
    assert system["role"] == "system" and "123,456원" in system["content"]

    r2 = client.post("/api/chat", json={"message": "최고는?", "conversation_id": body["conversation_id"]})
    assert r2.json()["conversation_id"] == body["conversation_id"]
    # 이전 대화가 GPT 입력에 포함되는지
    assert len(client.captured["messages"]) == 4

    convs = client.get("/api/conversations").json()
    assert len(convs) == 1 and convs[0]["message_count"] == 4 and "messages" not in convs[0]
    detail = client.get(f"/api/conversations/{body['conversation_id']}").json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant", "user", "assistant"]

    assert client.post("/api/chat", json={"message": "hi", "conversation_id": "nope"}).status_code == 404


def test_conversation_save_and_delete(client):
    r = client.post("/api/conversations", json={"messages": [{"role": "user", "content": "안녕"}]})
    assert r.status_code == 201 and r.json()["title"] == "안녕"
    cid = r.json()["id"]
    assert client.delete(f"/api/conversations/{cid}").status_code == 200
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.post("/api/conversations", json={"messages": []}).status_code == 422


def test_missing_config_returns_500_with_cors(monkeypatch):
    from app.services import data_service
    from main import app

    def boom():
        from app.firebase import ConfigError
        raise ConfigError("FIREBASE_SERVICE_ACCOUNT_JSON 환경 변수가 설정되지 않았습니다.")

    monkeypatch.setattr(data_service, "get_db", boom)
    r = TestClient(app).get("/api/data", headers={"Origin": "http://localhost:5500"})
    assert r.status_code == 500 and "설정 오류" in r.json()["detail"]
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5500"
