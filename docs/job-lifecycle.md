# Job Lifecycle

## Statuses

- `queued`: upload accepted and stored, waiting for the worker
- `running`: worker claimed the job and started generation
- `succeeded`: outputs saved and ready for gallery display
- `failed`: generation or storage failed, with `error_message` recorded

## Main records

- `GenerationJob`: owner link, style, input asset, timestamps, status
- `GenerationResult`: output asset, thumb asset, seed, dimensions, ordering index

## Frontend behavior

- The client polls every 3 seconds while a job is not terminal
- Result pages reopen by `job_id`
- Job history is filtered either by `guest_session_id` or by validated Telegram user id
