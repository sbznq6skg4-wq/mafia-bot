import asyncio
import logging
import sys
import os

# Papka yo'lini to'g'rilash uchun
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)

from config import BOT_TOKEN
from database import postgres, redis_db
from handlers import group, private
