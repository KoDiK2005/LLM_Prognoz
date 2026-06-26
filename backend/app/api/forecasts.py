import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun, ForecastRunStatus
from app.models.llm_insight import LLMInsight
from app.schemas.forecast_run import ForecastRunCreate, ForecastRunOut
from app.schemas.llm_insight import GenerateInsightsRequest, LLMInsightOut
from app.services import storage
from app.services.data_validation import DataValidationError, parse_and_clean_csv
from app.services.forecasting import run_forecast
from app.services.insights import generate_insight

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


async def _get_owned_run(run_id: uuid.UUID, db: AsyncSession) -> ForecastRun:
    user = await get_current_user(db)
    result = await db.execute(select(ForecastRun).where(ForecastRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None or run.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return run


@router.get("/{run_id}", response_model=ForecastRunOut)
async def get_forecast_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> ForecastRun:
    return await _get_owned_run(run_id, db)


@router.post("/{run_id}/insights", response_model=list[LLMInsightOut], status_code=201)
async def create_insights(
    run_id: uuid.UUID, payload: GenerateInsightsRequest, db: AsyncSession = Depends(get_db)
) -> list[LLMInsight]:
    run = await _get_owned_run(run_id, db)
    if run.status != ForecastRunStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Forecast run is not completed yet")

    dataset = await db.get(Dataset, run.dataset_id)

    insights = []
    for provider in payload.providers:
        insight = await generate_insight(run, dataset, provider)
        db.add(insight)
        insights.append(insight)

    await db.commit()
    for insight in insights:
        await db.refresh(insight)
    return insights


@router.get("/{run_id}/insights", response_model=list[LLMInsightOut])
async def list_insights(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[LLMInsight]:
    run = await _get_owned_run(run_id, db)
    result = await db.execute(
        select(LLMInsight)
        .where(LLMInsight.forecast_run_id == run.id)
        .order_by(LLMInsight.created_at.desc())
    )
    return list(result.scalars().all())
