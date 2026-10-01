import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

import group
import postgres
import private
import redis_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def set_bot_commands(bot: Bot) -> None:
    private_commands = [
        BotCommand(command="start", description="🔄 Botni qayta boshlash"),
        BotCommand(command="profile", description="👤 Mening profilim"),
        BotCommand(command="shop", description="🛍 Do'kon"),
        BotCommand(command="olmos", description="💎 Olmos sotib olish"),
    ]
    await bot.set_my_commands(commands=private_commands, scope=BotCommandScopeAllPrivateChats())

    group_commands = [
        BotCommand(command="game", description="🎮 O'yin yaratish"),
        BotCommand(command="start", description="▶️️ O'yinni muddatidan oldin boshlash (admin)"),
        BotCommand(command="roles", description="🎭 O'yin rollarini ko'rish"),
        BotCommand(command="leave", description="🚪 Ro'yxatdan chiqish"),
        BotCommand(command="stop", description="⛔️ O'yinni to'xtatish"),
    ]
    await bot.set_my_commands(commands=group_commands, scope=BotCommandScopeAllGroupChats())


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(private.router)
    dp.include_router(group.router)

    await postgres.init_pool()
    await redis_db.init_redis()
    await set_bot_commands(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await postgres.close_pool()
        await redis_db.close_redis()


if __name__ == "__main__":
    asyncio.run(main())
