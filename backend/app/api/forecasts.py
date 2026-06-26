import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun, ForecastRunStatus
from app.schemas.forecast_run import ForecastRunCreate, ForecastRunOut
from app.services import storage
from app.services.data_validation import DataValidationError, parse_and_clean_csv
from app.services.forecasting import run_forecast

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.post("", response_model=ForecastRunOut, status_code=201)
async def create_forecast_run(
    payload: ForecastRunCreate, db: AsyncSession = Depends(get_db)
) -> ForecastRun:
    user = await get_current_user(db)

    dataset = await db.get(Dataset, payload.dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = ForecastRun(
        org_id=user.org_id,
        dataset_id=dataset.id,
        created_by=user.id,
        status=ForecastRunStatus.RUNNING,
        forecast_params={"horizon": payload.horizon},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        content = storage.read(dataset.storage_path)
        df = parse_and_clean_csv(
            content,
            dataset.column_mapping["date_column"],
            dataset.column_mapping["value_column"],
        )
        result = run_forecast(df, payload.horizon)
    except DataValidationError as exc:
        run.status = ForecastRunStatus.FAILED
        run.error_message = str(exc)
    except Exception as exc:  # noqa: BLE001 — surfaced to the user as a failed run
        run.status = ForecastRunStatus.FAILED
        run.error_message = f"Forecast failed: {exc}"
    else:
        run.status = ForecastRunStatus.COMPLETED
        run.result = result

    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{run_id}", response_model=ForecastRunOut)
async def get_forecast_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ForecastRun:
    user = await get_current_user(db)

    result = await db.execute(select(ForecastRun).where(ForecastRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None or run.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return run
