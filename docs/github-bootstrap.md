# GitHub Bootstrap

## What to create

- One repository named `avatar_ai`
- Issues enabled
- Projects enabled
- Discussions optional

## Useful GitHub CLI commands

Create the repository:

```bash
gh repo create avatar_ai --private --source . --remote origin --push
```

Search repositories for reference implementations:

```bash
gh search repos "ollama chat ui" --limit 10
gh search repos "fastapi openai compatible local llm" --limit 10
gh search repos "ai companion memory" --limit 10
```

Search code for reusable pieces:

```bash
gh search code "chat/completions language:Python fastapi" --limit 20
gh search code "Ollama language:Python role:system" --limit 20
gh search code "tts streaming language:Python" --limit 20
```

## Suggested first issues

- Add a small web UI
- Persist conversations locally
- Add avatar create and edit endpoints
- Add tests for avatar loading and prompt assembly
- Add provider adapters for Ollama and LM Studio presets
