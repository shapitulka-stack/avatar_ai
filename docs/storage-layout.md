# Storage Layout

## Local development

When `STORAGE_BACKEND=local`, files are written under `runtime/storage/`.

## Path layout

- `uploads/<job_id>/input.<ext>`: original upload
- `uploads/<job_id>/preview.webp`: preview thumb for status screens
- `results/<job_id>/<index>.<ext>`: generated outputs
- `thumbs/<job_id>/<index>.webp`: thumbnails for gallery cards and history

## Production target

Switch to `STORAGE_BACKEND=s3` and keep the same logical key layout in the configured bucket.
