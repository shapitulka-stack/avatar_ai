# Architecture

## Working shape

- React provides the browser studio UI
- FastAPI exposes API routes for style discovery, job creation, job polling, file access, chat, and integrations
- SQLite stores job metadata and result references through SQLModel
- Local filesystem storage keeps uploads and generated assets during the MVP
- A worker loop processes queued jobs
- The generation layer can use a mock backend now and ComfyUI later
- Telegram can interact with the same backend via the bot entrypoint and WebApp validation utilities

## Browser flow

1. Frontend fetches styles from `/api/styles`
2. User uploads a portrait and chooses a style
3. Backend stores the upload and creates a queued job
4. Background processing or the worker claims the job
5. Generator returns assets and the backend stores them
6. Frontend polls `/api/jobs/{job_id}` and loads files from `/api/files/{key}`

## Telegram flow

1. User sends a portrait to the bot
2. Bot submits the image to `/api/jobs`
3. Bot polls the job status endpoint
4. When assets are ready, the bot sends them back into the chat

## Why this shape

- It keeps web and Telegram on one job API
- It works before the GPU server exists
- It leaves the generation backend swappable
- It keeps persistence simple and local-first
- It gives a clear seam where the future ComfyUI server will plug in
