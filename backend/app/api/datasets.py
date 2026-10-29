import json
import csv
import io
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.get("", response_model=list[dict])
def list_datasets():
    return DatasetService.list_datasets()

@router.get("/{dataset_id}", response_model=dict)
def get_dataset(dataset_id: str):
    ds = DatasetService.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds

@router.get("/{dataset_id}/examples", response_model=list[dict])
def get_dataset_examples(dataset_id: str, split: str = None, limit: int = 100, offset: int = 0):
    return DatasetService.get_examples(dataset_id, split=split, limit=limit, offset=offset)

@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    input_column: str = Form("input"),
    expected_column: str = Form("expected_output"),
    train_ratio: float = Form(0.7)
):
    filename = file.filename or "uploaded_dataset"
    raw_bytes = await file.read()

    # Security check: file size limit (5MB)
    if len(raw_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds limit of 5MB.")

    records = []
    content_str = raw_bytes.decode("utf-8", errors="replace")

    if filename.endswith(".json") or content_str.strip().startswith("["):
        try:
            records = json.loads(content_str)
            if not isinstance(records, list):
                raise HTTPException(status_code=400, detail="JSON dataset must contain a top-level list of objects.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file format: {str(e)}")
    else:
        try:
            reader = csv.DictReader(io.StringIO(content_str))
            records = [dict(row) for row in reader]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV file format: {str(e)}")

    try:
        new_ds = DatasetService.create_dataset_from_records(
            name=name,
            description=description,
            filename=filename,
            records=records,
            input_col=input_column,
            expected_col=expected_column,
            train_ratio=train_ratio
        )
        return new_ds
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
