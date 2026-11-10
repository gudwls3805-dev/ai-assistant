"""샘플 시계열 데이터(일별 매출) 생성 스크립트.

본인 데이터가 있다면 이 스크립트 대신 같은 형식(date,value,memo)의 CSV를
data/sample_sales.csv 자리에 두면 된다.

실행: python scripts/generate_sample_data.py
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "sample_sales.csv"
START = date(2026, 5, 1)
DAYS = 181  # 2026-05-01 ~ 2026-10-28

random.seed(42)
EVENTS = {
    date(2026, 5, 5): ("어린이날 특수", 1.6),
    date(2026, 6, 15): ("장마 시작", 0.75),
    date(2026, 7, 20): ("여름 프로모션", 1.45),
    date(2026, 8, 15): ("광복절 연휴", 1.3),
    date(2026, 9, 25): ("추석 연휴 휴무", 0.35),
    date(2026, 10, 9): ("한글날 이벤트", 1.5),
}

rows = []
for i in range(DAYS):
    d = START + timedelta(days=i)
    base = 150_000 + i * 450               # 완만한 상승 추세
    if d.weekday() in (4, 5):               # 금/토 매출 증가
        base *= 1.3
    elif d.weekday() == 0:                  # 월요일 약세
        base *= 0.85
    memo = ""
    if d in EVENTS:
        memo, factor = EVENTS[d]
        base *= factor
    value = round(max(base * random.gauss(1, 0.1), 0) / 100) * 100
    rows.append({"date": d.isoformat(), "value": int(value), "memo": memo})

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["date", "value", "memo"])
    w.writeheader()
    w.writerows(rows)
print(f"{len(rows)}개 데이터 생성 → {OUT}")
