from fastapi import APIRouter, HTTPException, Query
from .models import InspectionCreate, InspectionUpdate
from .inspection_service import create_inspection, list_inspections, get_inspection, update_inspection

router = APIRouter(prefix="/inspections", tags=["Inspection"])

@router.post("", status_code=201)
def post_inspection(payload: InspectionCreate):
    try:
        return create_inspection(payload)
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("")
def get_inspections(project_id: str | None = Query(None), inspector_id: str | None = Query(None),
                    status: str | None = Query(None)):
    return list_inspections(project_id, inspector_id, status)

@router.get("/{inspection_id}")
def get_one(inspection_id: str):
    item = get_inspection(inspection_id)
    if not item:
        raise HTTPException(404, "Inspection not found")
    return item

@router.put("/{inspection_id}")
def put_inspection(inspection_id: str, payload: InspectionUpdate):
    try:
        item = update_inspection(inspection_id, payload)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not item:
        raise HTTPException(404, "Inspection not found")
    return item
