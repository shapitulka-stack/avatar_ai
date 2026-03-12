from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, UsernameOccupiedError
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest, InviteToChannelRequest, UpdateUsernameRequest


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings
from app.telegram_account import as_entity_ref, as_public_username, channel_admin_rights


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage a Telegram user account with MTProto via Telethon.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("login", help="Authorize the user account and store the session locally.")

    create_channel = subparsers.add_parser("create-channel", help="Create a new public or private channel.")
    create_channel.add_argument("--title", required=True, help="Channel title.")
    create_channel.add_argument("--about", default="", help="Channel description/about text.")
    create_channel.add_argument("--username", help="Public @username for the channel.")
    create_channel.add_argument("--bot-username", help="Bot username to invite and promote, for example ai_ava_666_bot.")
    create_channel.add_argument("--bot-rank", default="Avatar Bot", help="Displayed admin rank for the bot.")

    send_post = subparsers.add_parser("send-post", help="Send a text post to a channel or chat.")
    send_post.add_argument("--target", required=True, help="Channel @username or inviteable entity reference.")
    send_post.add_argument("--text", help="Inline post text.")
    send_post.add_argument("--text-file", help="Path to a UTF-8 text file with the post body.")
    send_post.add_argument("--pin", action="store_true", help="Pin the sent message after publishing.")

    subparsers.add_parser("me", help="Print current account info.")
    return parser


async def _build_client() -> TelegramClient:
    settings = get_settings()
    if settings.telegram_account_api_id is None or not settings.telegram_account_api_hash:
        raise RuntimeError("Set TELEGRAM_ACCOUNT_API_ID and TELEGRAM_ACCOUNT_API_HASH before using telegram_account_cli.py")

    session_file = Path(settings.telegram_account_session_file)
    session_file.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(session_file), settings.telegram_account_api_id, settings.telegram_account_api_hash)


async def _login() -> None:
    settings = get_settings()
    client = await _build_client()
    async with client:
        phone = settings.telegram_account_phone
        await client.connect()
        if await client.is_user_authorized():
            me = await client.get_me()
            print(f"Already authorized as @{me.username or me.id}")
            return

        phone_value = phone or input("Telegram phone (international format): ").strip()
        code_request = await client.send_code_request(phone_value)
        code = input("Telegram login code: ").strip()
        try:
            await client.sign_in(phone=phone_value, code=code, phone_code_hash=code_request.phone_code_hash)
        except SessionPasswordNeededError:
            password = input("Telegram 2FA password: ").strip()
            await client.sign_in(password=password)

        me = await client.get_me()
        print(f"Authorized as @{me.username or me.id}")


async def _create_channel(title: str, about: str, username: str | None, bot_username: str | None, bot_rank: str) -> None:
    client = await _build_client()
    async with client:
        result = await client(
            CreateChannelRequest(
                title=title,
                about=about,
                megagroup=False,
                broadcast=True,
                for_import=False,
            )
        )
        channel = result.chats[0]
        print(f"Created channel: {channel.title} (id={channel.id})")

        public_username = as_public_username(username)
        if public_username:
            try:
                await client(UpdateUsernameRequest(channel=channel, username=public_username))
                print(f"Set public username: @{public_username}")
            except UsernameOccupiedError as exc:
                raise RuntimeError(f"Channel username @{public_username} is already taken.") from exc

        if bot_username:
            bot_ref = as_entity_ref(bot_username)
            bot_entity = await client.get_entity(bot_ref)
            await client(InviteToChannelRequest(channel=channel, users=[bot_entity]))
            await client(
                EditAdminRequest(
                    channel=channel,
                    user_id=bot_entity,
                    admin_rights=channel_admin_rights(),
                    rank=bot_rank,
                )
            )
            print(f"Invited and promoted bot: {bot_ref}")


def _load_post_text(inline_text: str | None, text_file: str | None) -> str:
    if inline_text:
        return inline_text
    if text_file:
        return Path(text_file).read_text(encoding="utf-8").strip()
    raise RuntimeError("Provide either --text or --text-file.")


async def _send_post(target: str, text: str, pin: bool) -> None:
    client = await _build_client()
    async with client:
        entity = await client.get_entity(target)
        message = await client.send_message(entity, text)
        print(f"Sent message id={message.id} to {target}")
        if pin:
            await client.pin_message(entity, message, notify=False)
            print("Pinned message")


async def _print_me() -> None:
    client = await _build_client()
    async with client:
        me = await client.get_me()
        print(f"id={me.id}")
        print(f"username=@{me.username}" if me.username else "username=<none>")
        print(f"name={me.first_name or ''} {me.last_name or ''}".strip())


async def _run() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "login":
        await _login()
        return
    if args.command == "create-channel":
        await _create_channel(args.title, args.about, args.username, args.bot_username, args.bot_rank)
        return
    if args.command == "send-post":
        text = _load_post_text(args.text, args.text_file)
        await _send_post(args.target, text, args.pin)
        return
    if args.command == "me":
        await _print_me()
        return

    raise RuntimeError(f"Unsupported command: {args.command}")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
