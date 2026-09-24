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

from database import postgres, redis_db
from handlers import group, private

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tokenni to'g'ridan-to'g'ri Railway muhit o'zgaruvchisidan olamiz
BOT_TOKEN = os.getenv("BOT_TOKEN")


async def set_bot_commands(bot: Bot) -> None:
    """Shaxsiy chat va guruh chatlari uchun alohida buyruqlar menyusini o'rnatadi."""
    private_commands = [
        BotCommand(command="start", description="🔄 Botni qayta boshlash"),
        BotCommand(command="profile", description="👤 Mening profilim"),
        BotCommand(command="shop", description="🛍 Do'kon"),
        BotCommand(command="olmos", description="💎 Olmos sotib olish"),
    ]
    await bot.set_my_commands(commands=private_commands, scope=BotCommandScopeAllPrivateChats())

    group_commands = [
        BotCommand(command="game", description="🎮 O'yin yaratish"),
        BotCommand(command="start", description="▶️ O'yinni muddatidan oldin boshlash (admin)"),
        BotCommand(command="roles", description="🎭 O'yin rollarini ko'rish"),
        BotCommand(command="leave", description="🚪 Ro'yxatdan chiqish"),
        BotCommand(command="stop", description="⛔️ O'yinni to'xtatish"),
    ]
    await bot.set_my_commands(commands=group_commands, scope=BotCommandScopeAllGroupChats())

    logger.info("Bot buyruqlari (shaxsiy va guruh uchun alohida) o'rnatildi.")


async def main() -> None:
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi! Railway Variables bo'limini tekshiring.")
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
