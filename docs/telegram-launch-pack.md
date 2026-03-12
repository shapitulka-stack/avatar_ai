# Telegram Launch Pack

Ready-to-use launch materials for the first private test of `avatar_ai`.

## Bot Setup Status

Already configured on the live bot:

- commands: `/start`, `/catalog`, `/top`, `/styles`
- menu button: `Открыть каталог`
- description and short description
- webhook: `https://avatar-ai-ngas.onrender.com/api/telegram/webhook`

Still required in BotFather:

- rotate the current bot token
- set mini app short name

## Sync Script

After rotating the token or changing the public URL, resync the bot from the repo:

```powershell
$env:RENDER_EXTERNAL_URL="https://avatar-ai-ngas.onrender.com"
$env:TELEGRAM_WEBAPP_URL="https://avatar-ai-ngas.onrender.com/studio"
$env:TELEGRAM_BOT_TOKEN="..."
backend\.venv\Scripts\python.exe backend\scripts\sync_telegram_bot.py
```

Use `--dry-run` first if you want to inspect the payloads without calling Telegram:

```powershell
backend\.venv\Scripts\python.exe backend\scripts\sync_telegram_bot.py --dry-run --external-url https://avatar-ai-ngas.onrender.com
```

## Direct Link Format

Once `TELEGRAM_MINI_APP_SHORT_NAME` is configured in BotFather, use these links:

- template link:
  `https://t.me/ai_ava_666_bot/<mini_app_short_name>?startapp=style-<style_id>`
- result link:
  `https://t.me/ai_ava_666_bot/<mini_app_short_name>?startapp=job-<job_id>`

For the current curated top set:

- `anime-neon`
- `cinematic-pro`
- `founder-brand`
- `velvet-royal`

## Channel Setup

Create one public test channel with:

- display name: `Avatar AI Top`
- handle fallback order:
  - `avatar_ai_top`
  - `avatar_ai_feed`
  - `avatar_ai_templates`

Suggested description:

`Топ шаблоны для AI-аватарок. Открывай пост, жми ссылку и вставляй себя в выбранный стиль прямо в mini app.`

Pin these two posts:

- welcome / how it works
- current top collection

## Ready Posts

Replace `<mini_app_short_name>` only after BotFather setup is complete.

### 1. Welcome / What This Is

Text:

`Это тестовый каталог AI-аватарок в Telegram.

Смотри топ шаблоны в канале, открывай понравившийся стиль и жми «Вставить себя».

Сначала загружаешь лицо один раз, дальше просто выбираешь стиль и получаешь готовую аву.`

CTA:

`https://t.me/ai_ava_666_bot/<mini_app_short_name>`

### 2. Top Anime Template

Text:

`Топ: Anime Neon

Яркая аниме-ава с неоном и сильным контрастом.

Если хочется заметную аватарку, начни с этого шаблона.`

CTA:

`https://t.me/ai_ava_666_bot/<mini_app_short_name>?startapp=style-anime-neon`

### 3. Top Cinematic / Business Template

Text:

`Топ: Cinematic Pro

Чистый кинематографичный портрет с дорогим светом.

Подходит для профиля, канала, экспертного образа и деловой аватарки.`

CTA:

`https://t.me/ai_ava_666_bot/<mini_app_short_name>?startapp=style-cinematic-pro`

### 4. Top Premium / Luxury Template

Text:

`Топ: Velvet Royal

Премиальный образ с дорогим вайбом и эффектной подачей.

Если хочется люкс-стиль без лишнего текста, это он.`

CTA:

`https://t.me/ai_ava_666_bot/<mini_app_short_name>?startapp=style-velvet-royal`

### 5. How It Works in 3 Taps

Text:

`Как это работает:

1. Открываешь шаблон
2. Загружаешь свое лицо
3. Жмешь «Вставить себя»

Когда аватар будет готов, бот вернет тебя прямо в результат.`

CTA:

`https://t.me/ai_ava_666_bot/<mini_app_short_name>`

## First Test Flow

1. Open the bot and check `/start`
2. Check `/top`
3. Open one template from `/top`
4. Save one face profile
5. Generate one result
6. Confirm the bot sends the result-return message
7. Publish the 5 prepared channel posts only after the direct link opens the mini app correctly
