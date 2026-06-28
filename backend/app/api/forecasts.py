import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun, ForecastRunStatus
from app.models.llm_insight import LLMInsight, LLMInsightStatus
from app.models.user import User
from app.schemas.forecast_run import ForecastRunCreate, ForecastRunOut
from app.schemas.llm_insight import AskQuestionRequest, AskQuestionResponse, GenerateInsightsRequest, LLMInsightOut
from app.services.insights import answer_question
from app.services.queue import get_queue

router = APIRouter(prefix="/forecasts", tags=["forecasts"])

_QUEUE_UNAVAILABLE_DETAIL = "Task queue is unavailable, please try again shortly"


async def _enqueue(job_name: str, *args: str) -> None:
    """Raises HTTPException(503) instead of an unhandled 500 if Redis is down."""
    try:
        queue = await get_queue()
        await queue.enqueue_job(job_name, *args)
    except (RedisError, OSError) as exc:
        raise HTTPException(status_code=503, detail=_QUEUE_UNAVAILABLE_DETAIL) from exc


@router.post("", response_model=ForecastRunOut, status_code=202)
async def create_forecast_run(
    payload: ForecastRunCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ForecastRun:
    dataset = await db.get(Dataset, payload.dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    run = ForecastRun(
        org_id=user.org_id,
        dataset_id=dataset.id,
        created_by=user.id,
        status=ForecastRunStatus.PENDING,
        forecast_params={"horizon": payload.horizon},
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    try:
        await _enqueue("run_forecast_job", str(run.id))
    except HTTPException:
        run.status = ForecastRunStatus.FAILED
        run.error_message = _QUEUE_UNAVAILABLE_DETAIL
        await db.commit()
        raise

    return run


@router.get("", response_model=list[ForecastRunOut])
async def list_forecast_runs(
    dataset_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ForecastRun]:
    dataset = await db.get(Dataset, dataset_id)
    if dataset is None or dataset.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Dataset not found")

    result = await db.execute(
        select(ForecastRun)
        .where(ForecastRun.dataset_id == dataset_id)
        .order_by(ForecastRun.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_owned_run(run_id: uuid.UUID, user: User, db: AsyncSession) -> ForecastRun:
    result = await db.execute(select(ForecastRun).where(ForecastRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None or run.org_id != user.org_id:
        raise HTTPException(status_code=404, detail="Forecast run not found")
    return run


@router.get("/{run_id}", response_model=ForecastRunOut)
async def get_forecast_run(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ForecastRun:
    return await _get_owned_run(run_id, user, db)


@router.delete("/{run_id}", status_code=204)
async def delete_forecast_run(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    run = await _get_owned_run(run_id, user, db)
    # llm_insights cascade-delete at the DB level.
    await db.delete(run)
    await db.commit()


@router.post("/{run_id}/insights", response_model=list[LLMInsightOut], status_code=202)
async def create_insights(
    run_id: uuid.UUID,
    payload: GenerateInsightsRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LLMInsight]:
    run = await _get_owned_run(run_id, user, db)
    if run.status != ForecastRunStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Forecast run is not completed yet")

    insights = [
        LLMInsight(forecast_run_id=run.id, provider=provider, model_name="")
        for provider in payload.providers
    ]
    db.add_all(insights)
    await db.commit()
    for insight in insights:
        await db.refresh(insight)

    try:
        for insight in insights:
            await _enqueue("generate_insight_job", str(insight.id))
    except HTTPException:
        for insight in insights:
            insight.status = LLMInsightStatus.FAILED
            insight.response_text = _QUEUE_UNAVAILABLE_DETAIL
        await db.commit()
        raise

    return insights


@router.post("/{run_id}/ask", response_model=AskQuestionResponse)
async def ask_question(
    run_id: uuid.UUID,
    payload: AskQuestionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AskQuestionResponse:
    run = await _get_owned_run(run_id, user, db)
    if run.status != ForecastRunStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Forecast run is not completed yet")

    dataset = await db.get(Dataset, run.dataset_id)
    answer, client = await answer_question(run, dataset, payload.provider, payload.question)
    return AskQuestionResponse(
        question=payload.question,
        answer=answer,
        provider=payload.provider,
        model_name=client.model_name,
    )


@router.get("/{run_id}/insights", response_model=list[LLMInsightOut])
async def list_insights(
    run_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LLMInsight]:
    run = await _get_owned_run(run_id, user, db)
    result = await db.execute(
        select(LLMInsight)
        .where(LLMInsight.forecast_run_id == run.id)
        .order_by(LLMInsight.created_at.desc())
    )
    return list(result.scalars().all())
