"""CSV 시계열 데이터 분석 (Firestore 없이 로컬에서 요약 확인).

실행: python scripts/analyze_csv.py [data/sample_sales.csv]
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.services.analysis import build_summary  # noqa: E402

path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "sample_sales.csv"
with path.open(encoding="utf-8") as f:
    items = [{"date": r["date"], "value": float(r["value"]), "memo": r.get("memo", "")} for r in csv.DictReader(f)]

print(json.dumps(build_summary(items), ensure_ascii=False, indent=2))
