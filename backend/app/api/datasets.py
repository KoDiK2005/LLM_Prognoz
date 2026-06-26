from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.dataset import DatasetOut
from app.services import storage
from app.services.data_validation import DataValidationError, parse_and_clean_csv

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetOut, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    date_column: str = Form(...),
    value_column: str = Form(...),
    name: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> Dataset:
    content = await file.read()

    try:
        parse_and_clean_csv(content, date_column, value_column)
    except DataValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = await get_current_user(db)
    storage_path = storage.save(user.org_id, file.filename or "upload.csv", content)

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
async def list_datasets(db: AsyncSession = Depends(get_db)) -> list[Dataset]:
    user = await get_current_user(db)
    result = await db.execute(
        select(Dataset).where(Dataset.org_id == user.org_id).order_by(Dataset.created_at.desc())
    )
    return list(result.scalars().all())
