import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from firebase_admin import firestore

from app.firebase import get_db
from app.schemas import DataCreate, DataItem, DataUpdate, DeleteResult, Summary
from app.services import data_service

router = APIRouter(prefix="/api/data", tags=["data"])

SAMPLE_CSV = Path(__file__).resolve().parents[2] / "data" / "sample_sales.csv"


@router.post("", response_model=DataItem, status_code=status.HTTP_201_CREATED, summary="새 데이터 추가")
def create_data(payload: DataCreate):
    return data_service.create_data(payload)


@router.get("", response_model=list[DataItem], summary="데이터 목록 조회 (날짜 오름차순)")
def list_data():
    return data_service.list_data()


@router.get("/summary", response_model=Summary, summary="데이터 요약 (프롬프트 주입용)")
def get_summary():
    return data_service.get_summary()


@router.post("/import-sample", status_code=status.HTTP_201_CREATED, summary="샘플 데이터(CSV) 일괄 등록 — data 컬렉션이 비어 있을 때만")
def import_sample():
    """backend/data/sample_sales.csv 를 Firestore data 컬렉션에 한 번에 넣는다.

    중복 등록을 막기 위해 컬렉션에 데이터가 이미 있으면 409를 반환한다.
    """
    db = get_db()
    col = db.collection(data_service.COLLECTION)
    if any(True for _ in col.limit(1).stream()):
        raise HTTPException(status_code=409, detail="이미 데이터가 있어 샘플을 등록하지 않았습니다. (중복 방지)")
    if not SAMPLE_CSV.exists():
        raise HTTPException(status_code=500, detail="샘플 CSV 파일을 찾을 수 없습니다.")

    with SAMPLE_CSV.open(encoding="utf-8") as f:
        rows = [DataCreate(date=r["date"], value=r["value"], memo=r.get("memo", "")) for r in csv.DictReader(f)]

    batch, count = db.batch(), 0
    for row in rows:
        batch.set(col.document(), {
            "date": row.date.isoformat(),
            "value": row.value,
            "memo": row.memo,
            "created_at": firestore.SERVER_TIMESTAMP,
        })
        count += 1
        if count % 400 == 0:  # Firestore 배치 한도(500) 이하로 나눠 커밋
            batch.commit()
            batch = db.batch()
    batch.commit()
    return {"imported": count}


@router.put("/{item_id}", response_model=DataItem, summary="데이터 수정 (보낸 필드만 변경)")
def update_data(item_id: str, payload: DataUpdate):
    try:
        item = data_service.update_data(item_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if item is None:
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return item


@router.delete("/{item_id}", response_model=DeleteResult, summary="데이터 삭제")
def delete_data(item_id: str):
    if not data_service.delete_data(item_id):
        raise HTTPException(status_code=404, detail="데이터를 찾을 수 없습니다.")
    return {"id": item_id}
