export type ForecastRunStatus = "pending" | "running" | "completed" | "failed";
export type LLMInsightStatus = "pending" | "completed" | "failed";
export type LLMProvider = "openai" | "anthropic" | "google" | "ollama";

export interface Dataset {
  id: string;
  name: string;
  column_mapping: { date_column: string; value_column: string };
  created_at: string;
}

export interface ForecastPoint {
  date: string;
  value: number;
}

export interface ForecastResult {
  model: string;
  freq: string;
  seasonal_periods: number | null;
  horizon: number;
  history: ForecastPoint[];
  forecast: ForecastPoint[];
}

export interface ForecastRun {
  id: string;
  dataset_id: string;
  status: ForecastRunStatus;
  forecast_params: { horizon: number };
  result: ForecastResult | null;
  error_message: string | null;
  created_at: string;
}

export interface LLMInsight {
  id: string;
  provider: LLMProvider;
  model_name: string;
  status: LLMInsightStatus;
  response_text: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: string;
  created_at: string;
}
