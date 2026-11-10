from fastapi import APIRouter, HTTPException, status

from app.schemas import DataCreate, DataItem, DataUpdate, DeleteResult, Summary
from app.services import data_service

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("", response_model=DataItem, status_code=status.HTTP_201_CREATED, summary="새 데이터 추가")
def create_data(payload: DataCreate):
    return data_service.create_data(payload)


@router.get("", response_model=list[DataItem], summary="데이터 목록 조회 (날짜 오름차순)")
def list_data():
    return data_service.list_data()


@router.get("/summary", response_model=Summary, summary="데이터 요약 (프롬프트 주입용)")
def get_summary():
    return data_service.get_summary()


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
