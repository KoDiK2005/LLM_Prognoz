from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun
from app.models.llm_insight import LLMInsight, LLMInsightStatus, LLMProvider
from app.services.llm.base import LLMClient
from app.services.llm.registry import get_client

# Cap how many raw (date, value) points go into a question prompt — enough
# for the LLM to reference specific values without blowing up token usage
# on a long history.
_MAX_POINTS_IN_PROMPT = 60


def build_prompt(forecast_run: ForecastRun, dataset: Dataset) -> str:
    result = forecast_run.result
    history = result["history"]
    forecast = result["forecast"]

    first_value = history[0]["value"]
    last_actual = history[-1]["value"]
    last_forecast = forecast[-1]["value"]
    pct_change = ((last_forecast - last_actual) / last_actual) * 100 if last_actual else 0

    return f"""You are a business analyst. Explain this forecast in plain language
for a non-technical stakeholder. Be concise (3-5 sentences). Mention the
overall trend, whether there's a recurring pattern, and call out anything
that looks like it needs attention.

Dataset: {dataset.name}
Model: {result["model"]} (seasonal period: {result.get("seasonal_periods") or "none detected"})
History: {len(history)} points, from {first_value:.2f} to {last_actual:.2f}
Forecast horizon: {len(forecast)} points
Projected value at end of horizon: {last_forecast:.2f} ({pct_change:+.1f}% vs last actual)
"""


async def fill_insight(insight: LLMInsight, forecast_run: ForecastRun, dataset: Dataset) -> LLMInsight:
    """Run the LLM call and write the result onto an existing (pending) insight row.

    Never raises — a provider failure (e.g. an unreachable self-hosted
    Ollama) is recorded as a failed insight rather than raised, so one bad
    provider doesn't fail the whole batch of queued jobs.
    """
    client = get_client(insight.provider)
    insight.model_name = client.model_name
    prompt = build_prompt(forecast_run, dataset)

    try:
        response = await client.generate(prompt)
    except Exception as exc:  # noqa: BLE001 — surfaced to the user as the insight text
        insight.status = LLMInsightStatus.FAILED
        insight.response_text = f"Error generating insight: {exc}"
        return insight

    insight.status = LLMInsightStatus.COMPLETED
    insight.response_text = response.text
    insight.prompt_tokens = response.prompt_tokens
    insight.completion_tokens = response.completion_tokens
    insight.cost_usd = response.cost_usd
    return insight


def build_question_prompt(forecast_run: ForecastRun, dataset: Dataset, question: str) -> str:
    """Answering a free-form question means the LLM needs the actual
    series, not just the summary stats build_prompt() uses — so embed the
    (capped) raw history/forecast points directly in the prompt instead of
    real tool-use function calling, which would mean juggling three
    different providers' incompatible tool-call APIs for a side project
    this size. Simpler, and just as capable for a bounded series.
    """
    result = forecast_run.result
    history = result["history"][-_MAX_POINTS_IN_PROMPT:]
    forecast = result["forecast"]

    history_str = ", ".join(f"{p['date'][:10]}={p['value']:.2f}" for p in history)
    forecast_str = ", ".join(f"{p['date'][:10]}={p['value']:.2f}" for p in forecast)

    return f"""You are a business analyst answering a question about a forecast.
Use the data below to answer precisely and concisely (2-4 sentences). If the
question can't be answered from this data, say so plainly.

Dataset: {dataset.name}
Model: {result["model"]} (seasonal period: {result.get("seasonal_periods") or "none detected"})
Historical values (most recent {len(history)} points): {history_str}
Forecast values: {forecast_str}

Question: {question}
"""


async def answer_question(
    forecast_run: ForecastRun, dataset: Dataset, provider: LLMProvider, question: str
) -> tuple[str, LLMClient]:
    """Returns (answer_text, client) — never raises; a provider failure is
    surfaced as the answer text, same pattern as fill_insight().
    """
    client = get_client(provider)
    prompt = build_question_prompt(forecast_run, dataset, question)
    try:
        response = await client.generate(prompt)
    except Exception as exc:  # noqa: BLE001 — surfaced to the user as the answer text
        return f"Error generating answer: {exc}", client
    return response.text, client
