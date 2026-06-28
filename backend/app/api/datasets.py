from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.dataset import DatasetOut
from app.services import storage
from app.services.data_validation import DataValidationError, parse_and_clean_csv

router = APIRouter(prefix="/datasets", tags=["datasets"])

_CHUNK_SIZE = 1024 * 1024


async def _read_with_limit(file: UploadFile) -> bytes:
    """Read in chunks and abort early once over the limit, rather than
    trusting Content-Length (which a client can omit or misreport).
    """
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    chunks = bytearray()
    while chunk := await file.read(_CHUNK_SIZE):
        chunks.extend(chunk)
        if len(chunks) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {settings.max_upload_size_mb}MB limit",
            )
    return bytes(chunks)


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    date_column: str = Form(...),
    value_column: str = Form(...),
    name: str = Form(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dataset:
    content = await _read_with_limit(file)

    try:
        parse_and_clean_csv(content, date_column, value_column)
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    storage_path = await storage.save(user.org_id, file.filename or "upload.csv", content)

    dataset = Dataset(
        org_id=user.org_id,
        uploaded_by=user.id,
        name=name,
        storage_path=storage_path,
        column_mapping={"date_column": date_column, "value_column": value_column},
    )
    db.add(dataset)
    await db.commit()
    await db.refresh(dataset)
    return dataset


@router.get("", response_model=list[DatasetOut])
async def list_datasets(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[Dataset]:
    result = await db.execute(
        select(Dataset).where(Dataset.org_id == user.org_id).order_by(Dataset.created_at.desc())
    )
    return list(result.scalars().all())
