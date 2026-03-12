# Integration Control Layer

## Role after the pivot

The integration layer is no longer the product itself. It is now the control plane around the avatar image service.

## What it still does

- GitHub API status and search endpoints
- Notion API status and search endpoint
- Search and browser tooling status checks
- GPU or ComfyUI worker API health checks
- Logging and monitoring status reporting

## Why keep it

It gives the product one place to verify source access, research tooling, and worker availability while the main user experience lives in the image-generation API and frontend.
