"""CSV 데이터를 Firestore `data` 컬렉션에 일괄 업로드한다.

실행:
  python scripts/seed_firestore.py              # 추가 업로드
  python scripts/seed_firestore.py --reset      # 기존 data 컬렉션 비운 뒤 업로드
  python scripts/seed_firestore.py my.csv --reset
"""
import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from firebase_admin import firestore  # noqa: E402

from app.firebase import get_db  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("csv_path", nargs="?", default=str(ROOT / "data" / "sample_sales.csv"))
parser.add_argument("--reset", action="store_true", help="기존 data 컬렉션 삭제 후 업로드")
args = parser.parse_args()

db = get_db()
col = db.collection("data")

if args.reset:
    deleted = 0
    for doc in col.stream():
        doc.reference.delete()
        deleted += 1
    print(f"기존 문서 {deleted}개 삭제")

with open(args.csv_path, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

batch, count = db.batch(), 0
for r in rows:
    batch.set(col.document(), {
        "date": r["date"],
        "value": float(r["value"]),
        "memo": r.get("memo", ""),
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    count += 1
    if count % 400 == 0:  # Firestore 배치 한도(500) 이하로 끊어서 커밋
        batch.commit()
        batch = db.batch()
batch.commit()
print(f"{count}개 문서 업로드 완료")
