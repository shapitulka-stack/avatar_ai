# Backend

The backend owns the Telegram-first MVP API surface:

- template feed endpoints
- face profile storage and retrieval
- job creation, queue metadata, and history
- worker-driven mock generation
- file delivery for previews and results
- Telegram WebApp identity validation and bot entrypoints

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Worker

For lightweight local development, creating a job also triggers `process_next_job()` in a FastAPI background task.

For a dedicated local worker loop, run:

```bash
python -m app.worker
```

## Main routes for the current MVP

- `GET /api/templates`
- `GET /api/me/face-profiles`
- `POST /api/me/face-profiles`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/me/jobs`
- `GET /api/files/{key}`

## Queue config

The backend uses these local queue settings:

- `QUEUE_MAX_CONCURRENT_JOBS`
- `QUEUE_MAX_PENDING_TOTAL`
- `QUEUE_MAX_PENDING_PER_USER`
- `QUEUE_ESTIMATED_SECONDS_PER_JOB`

## Generation backend

- `GENERATION_BACKEND=mock`: current alpha mode for end-to-end product testing
- Real face-swap/image infrastructure is intentionally out of scope for this release
