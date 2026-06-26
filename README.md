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

## Auth

- `POST /api/v1/auth/register` — создаёт organization + user (роль
  owner), возвращает JWT.
- `POST /api/v1/auth/login` — email+пароль → JWT.
- `GET /api/v1/auth/me` — текущий пользователь по токену.
- Все остальные эндпоинты (`datasets`, `forecasts`) требуют
  `Authorization: Bearer <token>` и работают только в рамках org
  пользователя из токена — проверено: пользователь другой организации
  не видит чужие datasets и не может запустить forecast на чужом dataset_id (404).
- Пароли — bcrypt, токены — JWT (HS256, `SECRET_KEY` из `.env`).

## Self-hosted LLM (Ollama)

Кроме облачных провайдеров (OpenAI/Anthropic) есть провайдер `ollama` —
открытая модель, запущенная локально через [Ollama](https://ollama.com),
без внешних API-ключей и без отправки данных третьим лицам.

- `docker-compose.yml` — сервис `ollama` (CPU по умолчанию).
- `docker-compose.gpu.yml` — оверрайд с GPU-резервацией (NVIDIA Container
  Toolkit), для машины с GPU:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
  docker compose exec ollama ollama pull llama3.1:8b   # или qwen2.5:14b на 16GB VRAM
  ```
  Модель задаётся через `OLLAMA_MODEL` в `.env` (дефолт — `llama3.2:1b`,
  маленькая модель для CPU/слабых машин).
- `app/services/llm/ollama_client.py` — HTTP-клиент к `/api/generate`.
  Подключается в `registry.py` без проверки ключа (self-hosted = всегда
  доступен, если сервер поднят).
- Если Ollama недоступна, `generate_insight()` не валит весь запрос —
  записывает ошибку как текст инсайта для этого провайдера, остальные
  провайдеры в батче всё равно отрабатывают.

**Не проверено end-to-end** на этой машине: здесь нет NVIDIA GPU (только
встроенная Intel-графика) и было мало места на диске (Docker Desktop
сам подчищал образы). Проверено статически — `docker compose config`
с GPU-оверрайдом валиден, приложение импортируется без ошибок. Реальный
прогон (pull модели + генерация) — на машине с RTX 5060 Ti.

## Статус

Итерация 6: self-hosted LLM провайдер через Ollama (CPU/GPU). Дальше —
очередь задач для долгих прогонов (Celery/Arq) и фронтенд UI.
