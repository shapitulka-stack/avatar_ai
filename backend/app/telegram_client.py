from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

import httpx

from app.config import Settings
from app.telegram_links import build_keyboard_button_payload


class TelegramAuthError(RuntimeError):
    pass


@dataclass
class TelegramIdentity:
    user_id: int
    username: str | None = None
    first_name: str | None = None


class TelegramBotService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def validate_init_data(self, init_data: str) -> TelegramIdentity:
        if not self.settings.telegram_bot_token:
            raise TelegramAuthError("TELEGRAM_BOT_TOKEN is not configured.")
        parsed = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            raise TelegramAuthError("Telegram init data is missing a hash.")

        auth_date = int(parsed.get("auth_date", "0") or 0)
        if auth_date and time.time() - auth_date > self.settings.telegram_init_data_ttl_seconds:
            raise TelegramAuthError("Telegram init data has expired.")

        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", self.settings.telegram_bot_token.encode("utf-8"), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
        if expected_hash != received_hash:
            raise TelegramAuthError("Telegram init data signature is invalid.")

        raw_user = parsed.get("user")
        if not raw_user:
            raise TelegramAuthError("Telegram init data does not include a user payload.")
        user = json.loads(raw_user)
        return TelegramIdentity(
            user_id=int(user["id"]),
            username=user.get("username"),
            first_name=user.get("first_name"),
        )

    async def handle_webhook(self, update: dict[str, Any]) -> dict[str, Any]:
        message = update.get("message") or update.get("edited_message") or {}
        text = (message.get("text") or "").strip()
        chat_id = message.get("chat", {}).get("id")
        if text.startswith("/start") and chat_id:
            await self.send_welcome(chat_id)
            return {"ok": True, "handled": True, "type": "start"}
        return {"ok": True, "handled": False}

    async def send_welcome(self, chat_id: int) -> None:
        reply_markup = {
            "inline_keyboard": [
                [
                    build_keyboard_button_payload(self.settings, text="Открыть каталог")
                ]
            ]
        }
        await self._send_message(
            chat_id,
            "Откройте avatar_ai прямо внутри Telegram: внутри каталог шаблонов, сохраненное лицо и быстрый запуск аватарок.",
            reply_markup,
        )

    async def send_generation_ready(self, user_id: int, job_id: str) -> None:
        reply_markup = {
            "inline_keyboard": [
                [build_keyboard_button_payload(self.settings, text="Открыть результат", job_id=job_id)],
                [build_keyboard_button_payload(self.settings, text="Открыть каталог")],
            ]
        }
        await self._send_message(user_id, "Аватар готов. Открывайте результат или возвращайтесь в каталог.", reply_markup)

    async def _send_message(self, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        if not self.settings.telegram_bot_token:
            return
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"https://api.telegram.org/bot{self.settings.telegram_bot_token}/sendMessage",
                json=payload,
            )
            response.raise_for_status()

