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

## Очередь задач (Arq + Redis)

Прогноз и генерация LLM-инсайтов выполняются не в HTTP-запросе, а в
отдельном воркере — иначе долгий прогон/LLM-вызов держал бы соединение
открытым и не масштабировался.

- `POST /api/v1/forecasts` и `POST /api/v1/forecasts/{run_id}/insights`
  теперь возвращают `202` и сразу создают записи со статусом `pending`
  (`ForecastRun.status` / `LLMInsight.status`), ставя задачу в очередь
  через `app/services/queue.py` (пул `arq`). Реальный результат —
  через `GET` по тому же ресурсу (поллинг).
- `app/worker.py` — `arq`-воркер (`run_forecast_job`,
  `generate_insight_job`), каждая задача открывает свою DB-сессию и
  обновляет статус (`running` → `completed`/`failed`).
- Сбой одного провайдера в батче инсайтов помечает только его запись
  `failed` — остальные обрабатываются независимо (как и раньше).
- `docker-compose.yml` — сервисы `redis` (брокер) и `worker` (тот же
  образ backend, команда `arq app.worker.WorkerSettings`).
- Используется Arq, а не Celery: проект async-first (FastAPI +
  SQLAlchemy async), Celery заточен под sync-воркеры и тащит лишнюю
  сложность (eventlet/gevent-обёртки) для async-кода.
- Проверено end-to-end локально: `docker compose up`, миграция
  `0002_llm_insight_status` применяется чисто, прогноз через очередь
  доходит до `completed`, инсайты — `completed` (mock) / `failed`
  (недоступная Ollama) без падения всего батча.

## Фронтенд

Next.js App Router, полностью client-side (auth/данные — через JWT в
`localStorage` и `fetch` к FastAPI, без серверных компонентов с доступом
к бэкенду).

- `/login`, `/register` — формы, сохраняют JWT и редиректят на `/dashboard`.
- `/dashboard` — единая страница: загрузка CSV (`DatasetUpload`), выбор
  датасета и горизонта, запуск прогноза с поллингом статуса (`pending` →
  `running` → `completed`/`failed`, раз в 1.5с), график (`ForecastChart`
  — лёгкий SVG без сторонних chart-библиотек), история прошлых прогонов
  по датасету (`RunHistory`, клик загружает график выбранного прогона),
  генерация LLM-инсайтов с выбором провайдеров — рендерятся side-by-side
  (`InsightsPanel`, CSS grid, не список друг под другом) для удобного
  сравнения интерпретаций разных LLM одного прогноза, с поллингом раз в
  2с, пока есть `pending`.
- `GET /api/v1/forecasts?dataset_id=` — список прогонов датасета
  (org-scoped), используется `RunHistory` для истории.
- `lib/api.ts` — обёртка над `fetch` с JWT-заголовком и обработкой ошибок
  (`ApiError`); `lib/types.ts` — типы, зеркалящие Pydantic-схемы бэкенда.
- Без auth-редиректа на сервере: `/dashboard` на клиенте проверяет токен
  в `useEffect` и шлёт на `/login`, если его нет.
- Next.js здесь 16.2.9 — конвенции отличаются от 13–15 (см.
  `frontend/AGENTS.md`); для client-heavy приложения с внешним auth
  Server Actions/Server Components не подходят, поэтому все страницы —
  `"use client"`.
- Проверено вручную в браузере (Chrome MCP): регистрация → загрузка
  датасета → несколько прогонов через очередь → история прогонов →
  клик по прошлому прогону подгружает его график → генерация инсайтов
  через OpenAI (mock) и Ollama (реальная модель `llama3.2:1b`) рядом
  side-by-side → logout → редирект неавторизованного пользователя на
  `/login`. Сама загрузка файла через `<input type="file">` не была
  прогнана через браузерный клик (sandbox не даёт грузить произвольные
  локальные файлы в headless-сессию) — датасет для теста загружен через
  API тем же пользователем, форма проверена статически (`tsc`, `eslint`,
  `next build`).

## Тесты

Backend:

```bash
docker compose up -d db redis
docker compose run --rm --no-deps backend pytest -v
```

- `backend/tests/conftest.py` — поднимает отдельную тестовую БД
  (`llm_prognoz_test`, авто-создаётся при первом запуске) на том же
  Postgres-сервере; перед каждым тестом схема пересоздаётся
  (`drop_all`/`create_all`) — простая и надёжная изоляция вместо
  транзакций-с-роллбэком, цена которой оправдана небольшим числом тестов.
- Очередь Arq не нужна живой: `get_queue()` в `app.api.forecasts`
  подменяется на `InlineQueue`, которая выполняет worker-функции
  (`run_forecast_job`, `generate_insight_job`) синхронно внутри запроса —
  тесты гоняют реальный код воркера, без Redis и отдельного процесса.
- 19 тестов: регистрация/логин/`/me`/дубликат email, загрузка датасета
  (валидный/невалидный CSV, мало точек, превышен лимит размера, изоляция
  по org), создание/чтение прогона (cross-org 404, история по датасету),
  генерация инсайтов (mock-провайдер → `completed`, недоступная Ollama →
  `failed`, недостроенный прогон → 400), недоступность очереди → `503`
  и прогон помечается `failed` вместо вечного `pending`, health-check.

Frontend (`frontend/lib/api.test.ts`, Vitest + jsdom):

```bash
cd frontend && npm test
```

- 8 тестов на `apiFetch`: JWT-заголовок (есть токен/нет токена),
  `Content-Type` для JSON vs `FormData`, парсинг `detail` из ответа
  бэкенда в `ApiError`, авто-логаут+редирект на `/login` при `401` с
  активным токеном — и что этого НЕ происходит при анонимном `401`
  (например, неверный пароль на `/auth/login`), `204 No Content`.

## CI

`.github/workflows/ci.yml` — на каждый push/PR в `master`:

- `backend-tests` — pytest против реального Postgres-сервиса.
- `migrations` — `alembic upgrade head` + `alembic downgrade base` на
  чистой БД (сьют тестов строит схему из моделей напрямую, минуя
  alembic, так что без этого шага сломанная миграция не была бы
  замечена CI вообще).
- `frontend-build` — `tsc`, `eslint`, `vitest`, `next build`.

`.github/dependabot.yml` — еженедельные обновления (pip/npm/
github-actions/docker), сгруппированные minor+patch, без авто-PR на
major-бампы базовых Docker-образов (Python/Node) — это нужно смотреть
руками, а не мержить не глядя.

## Обработка ошибок

- Если Redis/очередь недоступна на момент `POST /forecasts` или
  `POST /forecasts/{id}/insights`, запрос возвращает `503` вместо
  необработанного `500`, а уже созданная запись (`ForecastRun`/
  `LLMInsight`) сразу помечается `failed` с понятным сообщением — вместо
  того чтобы зависнуть в `pending` навсегда.
- CORS origins теперь настраиваются через `CORS_ORIGINS` в `.env`
  (через запятую), а не зашиты в код — нужно для деплоя на домен,
  отличный от `localhost:3000`.
- `POST /datasets/upload` читает файл чанками по 1MB и обрывает загрузку
  с `413`, если превышен `MAX_UPLOAD_SIZE_MB` (по умолчанию 10) — раньше
  `file.read()` без лимита буферизовал весь файл в память целиком.
- `GET /health` теперь реально проверяет БД (`SELECT 1`), а не всегда
  отвечает `{"status": "ok"}` — на этот эндпоинт смотрит healthcheck
  `backend`-сервиса в docker-compose, и раньше он бы не заметил
  отвалившийся пул соединений к Postgres.
- Frontend: `apiFetch` на `401` с активным токеном сам разлогинивает
  (чистит `localStorage`) и редиректит на `/login` — раньше истёкший
  токен просто бесконечно проваливал поллинг без объяснения. Ошибки
  загрузки списка датасетов/истории прогонов теперь показываются
  пользователю, а не проглатываются молча.

## Статус

Итерации 10–11: продакшенизация. Backend — pytest (19 тестов, реальная
Postgres), обработка отказа очереди задач, настраиваемый CORS, лимит на
размер загрузки, health-check с проверкой БД. Frontend — Vitest-тесты
на `apiFetch`, авто-логаут на истёкший токен, видимые ошибки загрузки.
CI на GitHub Actions (backend tests + миграции + frontend
tsc/eslint/vitest/build) гоняется на каждый push/PR в `master`;
Dependabot держит зависимости свежими без шума от мажорных бампов.
Прошла внутренний security-review без находок. Self-hosted Ollama
остаётся основным бесплатным LLM-провайдером для разработки. Дальше —
на выбор: реальные платные ключи (когда понадобится), или дальнейший
UI-полиш.
