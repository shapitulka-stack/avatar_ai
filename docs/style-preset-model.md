# Style Presets

## Storage

Each style lives in `data/styles/<style-id>.yaml`.

## Fields

- `id`: stable style key used by the API
- `name`: public label shown in the UI
- `description`: one-line UX description
- `prompt_template`: positive prompt fragment injected into the workflow
- `negative_prompt`: optional negative prompt fragment
- `preview_image`: path to the preview asset in the frontend public folder
- `enabled`: whether the style is available to users
- `width` and `height`: target output size for the workflow
- `output_count`: number of expected outputs
- `tags`: small labels for the style picker

## Current policy

- Styles are curated and fixed for `v1`
- Users do not edit prompts directly in the MVP
- Safe-only presets are the default
