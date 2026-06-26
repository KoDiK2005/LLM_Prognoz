# LLM Prognoz

SaaS-платформа для прогнозов по данным пользователя: статистическая/ML-модель
считает числовой прогноз, а несколько LLM (OpenAI, Anthropic, Google и др.)
объясняют результат, отвечают на вопросы и сравнивают интерпретации.

## Архитектура

- **Числа считает не LLM.** Прогноз строит statistical/ML-модель (Prophet,
  ARIMA, XGBoost) — это надёжнее и дешевле, чем просить LLM предсказывать
  значения временного ряда напрямую.
- **LLM отвечает за интерпретацию.** Объяснение тренда, ответы на вопросы
  пользователя через function calling, сравнение "точек зрения" разных
  провайдеров на один и тот же прогноз.
- **Прогоны версионируются.** Каждый прогноз хранит снэпшот данных,
  параметры модели и LLM-выводы, чтобы историю и сравнения можно было
  показать в UI.
- **Мультитенантность с самого начала** — изоляция данных по
  пользователю/организации.

Пайплайн:

```
upload data → validate/clean → forecast engine (Prophet/XGBoost)
            → forecast result (numbers + chart data)
            → LLM(s) generate narrative/insights
            → store run (data snapshot + model params + LLM outputs)
```

## Стек

- **Backend:** FastAPI + SQLAlchemy (async) + PostgreSQL
- **Frontend:** Next.js (TypeScript, App Router, Tailwind)
- **Инфраструктура:** Docker Compose для локальной разработки

## Структура репозитория

```
backend/    FastAPI приложение
frontend/   Next.js приложение
docker-compose.yml
```

## Запуск локально

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- Backend: http://localhost:8000/api/v1/health
- Frontend: http://localhost:3000

Применить миграции (после `docker compose up -d db`):

```bash
docker compose run --rm backend python -m alembic upgrade head
```

## Схема данных

- `organizations`, `users` — мультитенантность с самого начала.
- `datasets` — загруженный пользователем источник данных (файл +
  маппинг колонок: какая колонка дата, какая значение).
- `forecast_runs` — один версионированный прогон: параметры модели,
  числовой результат, статус. Снэпшот данных — через `dataset_id` +
  `created_at` прогона.
- `llm_insights` — интерпретации одного прогона разными LLM-провайдерами
  (несколько строк на один `forecast_run_id`).

## Движок прогноза

- `POST /api/v1/datasets/upload` — загрузка CSV (multipart: `file`,
  `date_column`, `value_column`, `name`). Валидация и очистка ряда
  (парсинг дат, приведение к регулярной частоте, интерполяция пропусков)
  происходит сразу при загрузке.
- `POST /api/v1/forecasts` — запускает прогноз по `dataset_id` на
  `horizon` точек вперёд, сохраняет результат на `forecast_runs`.
- Модель — Holt-Winters (statsmodels), а не Prophet: даёт тренд +
  сезонность без тяжёлых C++-зависимостей (cmdstan), которые сложно
  собрать без Visual Studio Build Tools. Сезонный период подбирается по
  частоте ряда (день → неделя, месяц → год и т.д.), если данных хватает
  на два полных цикла.
- Auth ещё нет — `app/api/deps.py` создаёт/использует одного dev-пользователя.
  Будет заменено в итерации с мультитенантным auth.

## LLM-интерпретации

- `POST /api/v1/forecasts/{run_id}/insights` — генерирует интерпретацию
  прогноза одной или несколькими LLM сразу (`{"providers": ["openai",
  "anthropic"]}`), каждая сохраняется отдельной строкой в `llm_insights`.
- `GET /api/v1/forecasts/{run_id}/insights` — список уже сгенерированных
  интерпретаций.
- Провайдер выбирается через `app/services/llm/registry.py`: если в
  `.env` задан ключ (`OPENAI_API_KEY`/`ANTHROPIC_API_KEY`) — используется
  реальный клиент, иначе — `MockLLMClient` (детерминированная заглушка).
  Google-клиент пока не реализован, всегда падает на mock.
- Добавить провайдера — реализовать `LLMClient.generate()` и подключить
  в `registry.py`, остальной пайплайн (промпт, хранение, API) не меняется.

## Статус

Итерация 4: LLM-интерпретации (multi-provider) с mock-фоллбеком на
отсутствующие ключи. Проверено end-to-end через Docker. Дальше — auth и
мультитенантность (сейчас `app/api/deps.py` — заглушка на один dev-аккаунт).
