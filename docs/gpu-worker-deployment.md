# GPU Worker Deployment

## Worker split

- API stays always on
- GPU worker is a separate runtime that runs `python -m app.worker`
- Worker talks to the same SQLite or future database and to the configured storage backend

## ComfyUI path

1. Provision a warm GPU pod.
2. Install ComfyUI and the required custom nodes for your chosen avatar workflow.
3. Export an API workflow JSON and place it at `data/workflows/avatar_v1.template.json` or point `COMFYUI_WORKFLOW_TEMPLATE` elsewhere.
4. Set `COMFYUI_BASE_URL` in `.env`.
5. Run the backend and worker.

## Development shortcut

Use `GENERATION_BACKEND=mock` until the remote workflow is stable.
