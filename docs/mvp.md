# MVP

## In scope

- One FastAPI backend service
- One Telegram-first React mini app
- Telegram bot and channel-friendly links that open the mini app on a specific template
- One browser debug/admin preview using guest sessions
- Static template feed from YAML in `data/styles`
- Saved face profiles per Telegram user or guest session
- Temporary face override uploads for one-off renders
- Local job persistence in SQLite
- Local storage for uploads and generated images
- Free-only queue limits and queue metadata in API responses
- Mock image generation for end-to-end product flow testing
- Telegram bot entrypoint that opens the mini app and returns users to results
- Bot `/top` flow for top templates and deep links into the catalog

## Out of scope

- Video or shorts generation
- Real face-swap or GPU generation backend
- Premium queue bypass
- Billing, payments, or subscriptions
- Public browser product experience
- Admin CRUD for templates
- Persona chat in the main user experience

## Success criteria

- The backend starts locally
- The mini app can list enabled templates
- A user can save a face profile and reuse it without uploading again
- A user can create a job from a saved face or a temporary override
- The API returns queue position, jobs ahead, wait estimate, and per-user pending limits
- The worker completes jobs with `GENERATION_BACKEND=mock`
- Result history works in both Telegram and browser debug mode
- The product flow stays Telegram-first even while local web debug remains available

## Suggested next milestones

1. Replace the mock image backend with a real face-swap/image generation backend
2. Add premium queue tiers and payments without changing the template/feed UX
3. Introduce template analytics and lightweight admin tooling
4. Add shorts/video after the image flow is stable and monetization assumptions are validated
