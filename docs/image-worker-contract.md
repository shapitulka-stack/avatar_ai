# Image Worker Contract

The app already supports two generator modes:

- `mock` for local placeholder renders
- `comfyui` for a real image server later

## Current expectation for ComfyUI mode

When `GENERATION_BACKEND=comfyui`, the worker talks directly to a ComfyUI instance through `COMFYUI_BASE_URL`.

The flow is:

1. Upload source image to `/upload/image`
2. Submit a rendered workflow to `/prompt`
3. Poll `/history/{prompt_id}`
4. Download outputs through `/view`

## Workflow template

The worker loads the API workflow template from:

`data/workflows/avatar_v1.template.json`

It replaces placeholders for:

- prompt
- negative prompt
- input image filename
- width and height
- output count
- seed
- client id
- style name

## Why this matters

This means the browser studio, job queue, storage, and Telegram flow are already decoupled from the server choice. The only missing piece in the separate server thread is the final ComfyUI box and workflow tuning.
