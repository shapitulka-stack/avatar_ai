# Telegram WebApp Flow

## User path

1. User opens the bot and sends `/start`.
2. Bot replies with an inline button that opens the web app.
3. The SPA reads `Telegram.WebApp.initData`.
4. Backend validates `initData` and binds jobs to `telegram_user_id`.
5. When a job finishes, the bot sends a short completion message with a deep-link back to the result page.

## Required config

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBAPP_URL`
- `TELEGRAM_WEBHOOK_SECRET` if webhook hardening is needed

## Notes

- Telegram identity is only used for job association and completion ping in `v1`
- Guest web users stay on a lightweight local session id instead of full auth
