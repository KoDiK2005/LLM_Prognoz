from app.models.dataset import Dataset
from app.models.forecast_run import ForecastRun
from app.models.llm_insight import LLMInsight, LLMProvider
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


async def generate_insight(forecast_run: ForecastRun, dataset: Dataset, provider: LLMProvider) -> LLMInsight:
    client = get_client(provider)
    prompt = build_prompt(forecast_run, dataset)
    response = await client.generate(prompt)

    return LLMInsight(
        forecast_run_id=forecast_run.id,
        provider=provider,
        model_name=client.model_name,
        response_text=response.text,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        cost_usd=response.cost_usd,
    )
