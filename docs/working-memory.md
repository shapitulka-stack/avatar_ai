# Working Memory

Lightweight project memory for `avatar_ai`. Update this file as work lands so the current goal, decisions, and next steps stay easy to recover in later sessions.

## Current Snapshot

- Last updated: 2026-03-12
- Product direction: Telegram-first avatar feed MVP with saved faces, template feed, free queue, and mock image generation
- Primary architecture: React mini app frontend, FastAPI backend, SQLite/Postgres-compatible job persistence, local file storage, and a lightweight job pipeline that can run locally or inside a single Render web service
- Current generation strategy: `mock` backend for product-shell validation before real face-swap integration
- Current delivery shape: Telegram Mini App first, browser debug/admin preview second

## Active Decisions

- Keep the user-facing flow focused on `save face -> choose template -> queue -> result`
- Keep queue tier responses in the API, but ship only `free` for this release
- Preserve saved face profiles and temporary override uploads as separate paths
- Leave persona chat and research/integration endpoints available in code, but out of the main product UX
- Keep templates static and editable in YAML until the feed proves useful

## What Is Already True

- The repo includes a working FastAPI backend, React frontend, Telegram entrypoint, and a lightweight background job loop
- Queue metadata and queue limits are part of the job API responses
- Mock generation completes end to end and stores results locally
- Browser mode still works for local QA with guest sessions
- Telegram validation is already wired for WebApp identity

## Next Useful Steps

- Push the repo to GitHub and run the prepared Render test deploy
- Connect a real face-swap/image backend behind the existing job flow
- Add premium tiers and payments on top of the free queue
- Measure which templates convert best before adding admin tooling
- Remove or archive more legacy product paths once the Telegram-first shape is stable

## Blockers Or Watchouts

- Do not let browser debug mode drift into a second consumer product
- Do not expand into video before the image queue loop is stable
- Keep docs aligned with the actual Telegram-first flow
- Preserve local-first development behavior even if cloud compute is added later

## Update Log

### 2026-03-12

- Added Render deployment scaffolding with a single Docker-based web service, Postgres blueprint, and in-process Telegram polling for free-tier testing
- Reframed the MVP around a Telegram Mini App avatar feed instead of a browser studio + persona chat experience
- Added queue metadata and queue limits to the backend job APIs
- Rebuilt the frontend around saved faces, template feed, queue status, and results
- Kept the generation backend on `mock` for the current alpha shell

### 2026-03-11

- Seeded a repo-local working memory file for future Codex and human check-ins
- Captured the current product direction, major decisions, and next-step priorities from the existing project docs

## Update Checklist

When updating this file, prefer touching only the sections that changed:

- Current Snapshot
- Active Decisions
- Next Useful Steps
- Blockers Or Watchouts
- Update Log
