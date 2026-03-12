# avatar_ai

Telegram-first avatar feed MVP for saved-face image renders.

## What this repo contains

- Telegram Mini App frontend for template feed, queue status, results, and history
- FastAPI backend for templates, face profiles, jobs, files, and Telegram identity
- Local worker flow with SQLite persistence and local asset storage
- Telegram bot entrypoint that opens the mini app and links users back to results
- Product docs that track the current MVP direction

## Current product shape

- User flow: save face once, choose a template, enter the free queue, view results
- Distribution flow: channel posts and bot messages drive traffic into the mini app catalog
- Media scope: image-only alpha
- Queue model: free-only for now, premium kept out of scope for this release
- Generation backend: `mock` for end-to-end flow validation
- Browser mode: debug/admin preview only, not the main consumer surface

## Quick start

1. Copy `.env.example` to `.env`
2. Start the backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

3. Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

4. Open [http://127.0.0.1:5173](http://127.0.0.1:5173) for browser debug preview
5. Optional: set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBAPP_URL`, then run the bot in a third terminal:

```bash
cd backend
.venv\Scripts\activate
python -m app.telegram_bot
```

6. Optional but recommended for channel-friendly direct links:

```env
TELEGRAM_BOT_USERNAME=your_bot_username
TELEGRAM_MINI_APP_SHORT_NAME=your_mini_app_short_name
```

With both values set, the bot can generate Telegram direct links that open the mini app on a specific template or result.

## Core API for the current MVP

- `GET /api/templates`
- `GET /api/me/face-profiles`
- `POST /api/me/face-profiles`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/me/jobs`
- `GET /api/files/{key}`

## Queue behavior

Queue responses now include:

- `queue_tier`
- `queue_position`
- `jobs_ahead`
- `estimated_wait_seconds`
- `user_pending_jobs`
- `max_pending_per_user`

Default local limits are configured through `.env.example`.

## Current alpha assumptions

- `GENERATION_BACKEND=mock`
- No video or shorts yet
- No premium payments yet
- Telegram is the main product surface
- Browser mode is only for local QA and admin/debug preview

## Render test deploy

A first cloud test deploy is prepared via [render.yaml](./render.yaml) and [Dockerfile](./Dockerfile).

- Service shape: one Render web service running FastAPI, the built mini app, and Telegram polling in the same container
- Database: one free Render Postgres instance
- Generation: `mock` by default for smoke-testing the Telegram flow
- Storage: local container storage for now, which is acceptable for short-lived alpha tests but not for durable production assets

Before Render can deploy, this repo must be pushed to GitHub, GitLab, or Bitbucket.

## Bot and channel flow

- `/start` opens the catalog entrypoint
- `/top` sends a short list of top templates with buttons that open the mini app on the selected template
- `/start style-anime-neon` opens the catalog on a specific template
- Result notifications from the bot open the finished job directly inside the mini app
- If `TELEGRAM_BOT_USERNAME` and `TELEGRAM_MINI_APP_SHORT_NAME` are configured, the same links can be reused in channel posts
