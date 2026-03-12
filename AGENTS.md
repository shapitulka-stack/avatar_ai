# AGENTS.md

## Project focus

Build a local-first avatar AI MVP with the smallest useful architecture.

## Product defaults

- First release is text-first
- Local LLM access is required
- Cloud dependencies are optional, not mandatory
- Notion stores product context and research
- GitHub stores code, issues, and change history

## Technical defaults

- Prefer Python for the backend
- Prefer FastAPI for local APIs
- Prefer OpenAI-compatible local endpoints so providers remain swappable
- Store avatar definitions in YAML or JSON before introducing a database
- Add frontend only after the chat loop works end to end

## Working rules

- Read `docs/vision.md` and `docs/mvp.md` before major changes
- Update docs when scope or architecture changes
- Keep modules small and typed
- Avoid premature abstractions and plugin systems
- Add environment variables to `.env.example` when introducing new config
- Preserve local-first behavior unless the user explicitly asks for cloud features

## Definition of useful progress

- The app can list avatars
- The app can send a prompt to a local model
- The app can keep a small avatar profile and memory block
- The docs stay aligned with what the code really does
