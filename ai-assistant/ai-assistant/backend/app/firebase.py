"""Firestore 클라이언트 (지연 초기화 싱글톤)."""
import json

import firebase_admin
from firebase_admin import credentials, firestore

from app.config import FIREBASE_SERVICE_ACCOUNT_JSON

_db = None


class ConfigError(RuntimeError):
    """필수 환경 변수 누락 등 서버 설정 오류."""


def get_db():
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        raw = FIREBASE_SERVICE_ACCOUNT_JSON.strip()
        if not raw:
            raise ConfigError("FIREBASE_SERVICE_ACCOUNT_JSON 환경 변수가 설정되지 않았습니다.")
        try:
            # '{' 로 시작하면 JSON 문자열, 아니면 키 파일 경로로 간주
            cred = credentials.Certificate(json.loads(raw) if raw.startswith("{") else raw)
        except Exception as e:  # 잘못된 JSON / 경로
            raise ConfigError(f"Firebase 서비스 계정 키를 읽을 수 없습니다: {e}") from e
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db
