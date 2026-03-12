# Frontend

The frontend is a Telegram-first React mini app for the current avatar feed MVP.

## Run

```bash
npm install
npm run dev
```

## Expected env

Set `VITE_API_BASE_URL` if the backend is not running at `http://127.0.0.1:8000`.

## Current screens

- Template feed
- Saved face profiles
- Temporary face override upload
- Queue status
- Result gallery
- Job history

## Product notes

- Telegram Mini App is the main user surface
- Browser mode is kept only for local QA/admin preview
- This release is image-only and free-only
- The UI is aligned to the mock-generation alpha flow, not a public web launch
