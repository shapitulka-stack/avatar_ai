from __future__ import annotations

import asyncio
import logging

from sqlmodel import Session

from app.config import get_settings
from app.db import create_db_and_tables, get_engine
from app.jobs import claim_next_queued_job, fail_job, input_filename_for_job, store_job_results
from app.storage import get_storage
from app.style_store import get_style
from app.telegram_client import TelegramBotService
from app.services.image_generator import AvatarGenerator


logger = logging.getLogger("avatar_ai.worker")
CLAIM_LOCK = asyncio.Lock()


async def process_next_job() -> bool:
    settings = get_settings()
    create_db_and_tables()
    processed_any = False

    while True:
        async with CLAIM_LOCK:
            with Session(get_engine()) as session:
                job = claim_next_queued_job(session, settings)

        if not job:
            return processed_any

        processed_any = True

        try:
            style = get_style(settings.style_dir, job.style_id)
            input_image = get_storage(settings).download(job.input_image_key).content
            generator = AvatarGenerator(settings)
            output = await generator.generate(style, input_image, job.id, input_filename_for_job(job))
            with Session(get_engine()) as session:
                stored_job = session.get(type(job), job.id)
                if not stored_job:
                    continue
                stored_job = store_job_results(session, settings, stored_job, output.assets, output.prompt_id)
            if stored_job.telegram_user_id:
                try:
                    await TelegramBotService(settings).send_generation_ready(stored_job.telegram_user_id, stored_job.id)
                except Exception:  # noqa: BLE001
                    logger.exception("Telegram notification failed for job %s", stored_job.id)
            logger.info("Processed job %s", job.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed job %s", job.id)
            with Session(get_engine()) as session:
                stored_job = session.get(type(job), job.id)
                if stored_job:
                    fail_job(session, stored_job, str(exc))


async def run_worker() -> None:
    settings = get_settings()
    while True:
        processed = await process_next_job()
        if not processed:
            await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(run_worker())
