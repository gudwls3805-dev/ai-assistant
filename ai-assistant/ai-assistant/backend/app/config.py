"""환경 변수 설정. 키/비밀 값은 코드에 두지 않고 .env 또는 배포 환경 변수로만 주입한다."""
import os

from dotenv import load_dotenv

load_dotenv()


def _list(name: str, default: str = "") -> list[str]:
    return [v.strip().rstrip("/") for v in os.getenv(name, default).split(",") if v.strip()]


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_MAX_TOKENS = int(os.getenv("OPENAI_MAX_TOKENS", "500"))  # 비용 보호용 토큰 상한

# JSON 문자열 전체 또는 키 파일 경로 둘 다 허용
FIREBASE_SERVICE_ACCOUNT_JSON = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")

# CORS 허용 도메인 (쉼표 구분). 예: https://my-app.vercel.app,http://localhost:5500
ALLOWED_ORIGINS = _list("ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500")
# 선택: Vercel 프리뷰 도메인 등 패턴 허용. 예: https://my-app-.*\.vercel\.app
ALLOWED_ORIGIN_REGEX = os.getenv("ALLOWED_ORIGIN_REGEX") or None

# 데이터 도메인 설명 (다른 시계열 데이터로 바꿀 때 수정)
DATA_LABEL = os.getenv("DATA_LABEL", "일별 매출")
DATA_UNIT = os.getenv("DATA_UNIT", "원")

# 채팅 시 GPT에 함께 보낼 이전 메시지 수 (토큰 절약)
CHAT_HISTORY_LIMIT = int(os.getenv("CHAT_HISTORY_LIMIT", "10"))
