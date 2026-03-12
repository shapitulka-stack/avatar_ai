import asyncio
import logging
from io import BytesIO
from pathlib import Path

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Update, WebAppInfo
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import Settings, get_settings


STYLE_PREFIX = "style:"
logger = logging.getLogger("avatar_ai.telegram_bot")


def _studio_markup(settings: Settings) -> InlineKeyboardMarkup:
    webapp_url = settings.public_telegram_webapp_url
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Открыть ленту", web_app=WebAppInfo(url=webapp_url))]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    await _reply(
        update,
        "Откройте mini app прямо внутри Telegram: там есть лента шаблонов, сохраненные лица и история задач. Если удобнее, можно по-прежнему отправить фото в этот чат и выбрать шаблон здесь.",
        reply_markup=_studio_markup(settings),
    )


async def styles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    items = await _fetch_styles(get_settings())
    lines = [f"- {item['name']}: {item['description']}" for item in items]
    await _reply(update, "Доступные пресеты:\n" + "\n".join(lines))


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    message = update.effective_message
    if message is None or not message.photo:
        return

    photo = message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    temp_dir = settings.bot_temp_dir / str(update.effective_user.id if update.effective_user else "anonymous")
    temp_dir.mkdir(parents=True, exist_ok=True)
    photo_path = temp_dir / f"{photo.file_unique_id}.jpg"
    await file.download_to_drive(custom_path=str(photo_path))

    context.user_data["pending_photo_path"] = str(photo_path)
    style_items = await _fetch_styles(settings)
    context.user_data["style_lookup"] = {item["id"]: item["name"] for item in style_items}
    keyboard = [[InlineKeyboardButton(item["name"], callback_data=f"{STYLE_PREFIX}{item['id']}")] for item in style_items]
    await _reply(
        update,
        "Фото сохранено. Выберите стиль, и я отправлю готовые аватары сюда же.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def handle_style_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.data is None:
        return

    await query.answer()
    pending_photo_path = context.user_data.get("pending_photo_path")
    if not pending_photo_path:
        await query.edit_message_text("Сначала отправьте фото, а потом выберите стиль.")
        return

    style_id = query.data.removeprefix(STYLE_PREFIX)
    style_lookup = context.user_data.get("style_lookup", {})
    style_name = style_lookup.get(style_id, style_id)
    job = await _submit_job(get_settings(), Path(pending_photo_path), style_id)

    context.user_data.pop("pending_photo_path", None)
    context.user_data.pop("style_lookup", None)

    chat_id = query.message.chat_id if query.message else update.effective_chat.id
    await query.edit_message_text(f"Запуск для «{style_name}» поставлен в очередь. ID задачи: {job['job_id']}.")
    asyncio.create_task(_poll_and_deliver(context.application, chat_id, job["job_id"], style_name))


async def _poll_and_deliver(application: Application, chat_id: int, job_id: str, style_name: str) -> None:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60) as client:
        for _ in range(120):
            response = await client.get(f"{_api_base(settings)}/api/jobs/{job_id}")
            response.raise_for_status()
            job = response.json()
            if job["status"] in {"queued", "running"}:
                await asyncio.sleep(3)
                continue

            if job["status"] == "failed":
                await application.bot.send_message(chat_id=chat_id, text=f"Задача завершилась ошибкой: {job.get('error_message') or 'неизвестная ошибка'}")
                return

            for index, result in enumerate(job["results"], start=1):
                image_response = await client.get(f"{_api_base(settings)}{result['image_url']}")
                image_response.raise_for_status()
                file_bytes = BytesIO(image_response.content)
                file_bytes.name = f"avatar-{index}.png"
                await application.bot.send_photo(
                    chat_id=chat_id,
                    photo=InputFile(file_bytes, filename=file_bytes.name),
                    caption=style_name if index == 1 else None,
                )
            return

    await application.bot.send_message(chat_id=chat_id, text=f"Задача {job_id} всё ещё обрабатывается. Откройте mini app в Telegram, чтобы проверить очередь.")


async def _fetch_styles(settings: Settings) -> list[dict[str, object]]:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{_api_base(settings)}/api/styles")
        response.raise_for_status()
        return response.json()


async def _submit_job(settings: Settings, photo_path: Path, style_id: str) -> dict[str, object]:
    data = {
        "style_id": style_id,
        "source": "web",
    }
    files = {
        "photo": (photo_path.name, photo_path.read_bytes(), "image/jpeg"),
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(f"{_api_base(settings)}/api/jobs", data=data, files=files)
        response.raise_for_status()
        return response.json()


def _api_base(settings: Settings) -> str:
    return settings.public_backend_base_url.rstrip("/")


async def _reply(update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    message = update.effective_message
    if message is not None:
        await message.reply_text(text, reply_markup=reply_markup)


def build_application(settings: Settings | None = None, *, use_updater: bool = True) -> Application:
    resolved_settings = settings or get_settings()
    if not resolved_settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before running the Telegram bot.")

    builder = Application.builder().token(resolved_settings.telegram_bot_token)
    if not use_updater:
        builder = builder.updater(None)
    application = builder.build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("app", start))
    application.add_handler(CommandHandler("styles", styles))
    application.add_handler(CallbackQueryHandler(handle_style_choice, pattern=f"^{STYLE_PREFIX}"))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return application


async def start_polling_application(application: Application) -> None:
    await application.initialize()
    await application.start()
    if application.updater is None:
        raise RuntimeError("Telegram updater is not available.")
    await application.updater.start_polling()
    logger.info("Telegram polling started")


async def start_webhook_application(application: Application, settings: Settings) -> None:
    webhook_url = settings.telegram_webhook_url
    if webhook_url is None:
        raise RuntimeError('Telegram webhook URL is not configured.')

    await application.initialize()
    await application.start()
    await application.bot.set_webhook(
        url=webhook_url,
        allowed_updates=Update.ALL_TYPES,
        secret_token=settings.telegram_webhook_secret_value,
    )
    logger.info('Telegram webhook configured at %s', webhook_url)


async def stop_polling_application(application: Application) -> None:
    if application.updater is not None:
        await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("Telegram polling stopped")


async def stop_webhook_application(application: Application) -> None:
    await application.stop()
    await application.shutdown()
    logger.info('Telegram webhook stopped')


def main() -> None:
    application = build_application()
    application.run_polling(close_loop=False)


if __name__ == "__main__":
    main()


