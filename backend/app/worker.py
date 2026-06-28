import uuid

from arq.connections import RedisSettings

from app.core.config import settings
from app.db.session import async_session
from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun, ForecastRunStatus
from app.models.llm_insight import LLMInsight
from app.services import storage
from app.services.data_validation import DataValidationError, parse_and_clean_csv
from app.services.forecasting import run_forecast
from app.services.insights import fill_insight


async def run_forecast_job(ctx: dict, run_id: str) -> None:
    async with async_session() as db:
        run = await db.get(ForecastRun, uuid.UUID(run_id))
        if run is None:
            return

        dataset = await db.get(Dataset, run.dataset_id)
        run.status = ForecastRunStatus.RUNNING
        await db.commit()

        try:
            content = await storage.read(dataset.storage_path)
            df = parse_and_clean_csv(
                content,
                dataset.column_mapping["date_column"],
                dataset.column_mapping["value_column"],
            )
            result = run_forecast(df, run.forecast_params["horizon"])
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


async def generate_insight_job(ctx: dict, insight_id: str) -> None:
    async with async_session() as db:
        insight = await db.get(LLMInsight, uuid.UUID(insight_id))
        if insight is None:
            return

        run = await db.get(ForecastRun, insight.forecast_run_id)
        dataset = await db.get(Dataset, run.dataset_id)

        await fill_insight(insight, run, dataset)
        await db.commit()


class WorkerSettings:
    functions = [run_forecast_job, generate_insight_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
