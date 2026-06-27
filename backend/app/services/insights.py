from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun
from app.models.llm_insight import LLMInsight, LLMInsightStatus
from app.services.llm.registry import get_client


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
