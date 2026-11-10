"""시계열 분석 로직 (순수 함수).

Firestore나 OpenAI에 의존하지 않으므로 CSV 분석 스크립트와 API 양쪽에서 재사용한다.
입력: [{"date": "YYYY-MM-DD", "value": float, "memo": str}, ...]
"""
from __future__ import annotations

import statistics
from collections import OrderedDict

TREND_THRESHOLD_PCT = 3.0  # ±3% 이내면 '유지'로 판단


def _r(x: float) -> float:
    return round(float(x), 2)


def _trend(values: list[float]) -> tuple[str, float | None]:
    """최근 N일 평균과 직전 N일 평균을 비교해 추세를 판단한다 (N = 최대 30)."""
    n = len(values)
    if n < 4:
        return "데이터 부족", None
    window = min(30, n // 2)
    recent = values[-window:]
    prev = values[-2 * window:-window]
    prev_mean = statistics.mean(prev)
    if prev_mean == 0:
        return "유지", 0.0
    change = (statistics.mean(recent) - prev_mean) / prev_mean * 100
    if change >= TREND_THRESHOLD_PCT:
        label = "상승"
    elif change <= -TREND_THRESHOLD_PCT:
        label = "하락"
    else:
        label = "유지"
    sign = "+" if change >= 0 else ""
    return f"{label} (최근 {window}일 평균이 직전 {window}일 대비 {sign}{change:.1f}%)", _r(change)


def _monthly(items: list[dict]) -> list[dict]:
    groups: "OrderedDict[str, list[float]]" = OrderedDict()
    for it in items:
        groups.setdefault(it["date"][:7], []).append(float(it["value"]))
    return [
        {"month": m, "count": len(v), "total": _r(sum(v)), "average": _r(statistics.mean(v))}
        for m, v in groups.items()
    ]


def build_summary(items: list[dict]) -> dict:
    """데이터 목록 → 프롬프트 주입용 요약 dict."""
    if not items:
        return {
            "period": "데이터 없음",
            "count": 0,
            "metrics": None,
            "trend": "데이터 부족",
            "trend_change_pct": None,
            "recent_7_days_average": None,
            "latest_month": None,
            "monthly": [],
        }

    items = sorted(items, key=lambda x: x["date"])
    values = [float(i["value"]) for i in items]
    max_item = max(items, key=lambda x: float(x["value"]))
    min_item = min(items, key=lambda x: float(x["value"]))
    trend, change = _trend(values)
    monthly = _monthly(items)

    # 가장 최근 달 vs 전체 일평균 비교 (예: "이번 달 실적이 어때?" 대응)
    overall_avg = statistics.mean(values)
    latest = dict(monthly[-1])
    latest["vs_overall_daily_avg_pct"] = (
        _r((latest["average"] - overall_avg) / overall_avg * 100) if overall_avg else None
    )

    return {
        "period": f"{items[0]['date']} ~ {items[-1]['date']}",
        "count": len(items),
        "metrics": {
            "total": _r(sum(values)),
            "average": _r(overall_avg),
            "max": _r(max_item["value"]),
            "max_date": max_item["date"],
            "min": _r(min_item["value"]),
            "min_date": min_item["date"],
            "std": _r(statistics.pstdev(values)),  # 보너스: 추가 지표(표준편차)
        },
        "trend": trend,
        "trend_change_pct": change,
        "recent_7_days_average": _r(statistics.mean(values[-7:])),
        "latest_month": latest,
        "monthly": monthly,
    }
