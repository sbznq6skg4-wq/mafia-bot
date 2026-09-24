import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! .env faylini yoki Railway Variables'ni tekshiring.")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL topilmadi! Neon PostgreSQL ulanish satrini qo'shing.")
if not REDIS_URL:
    raise ValueError("REDIS_URL topilmadi! Upstash Redis ulanish satrini qo'shing.")

# O'yin sozlamalari
MIN_PLAYERS = 4          # o'yin boshlanishi uchun minimal o'yinchilar soni
LOBBY_SECONDS = 120       # lobbi ochiq turadigan vaqt (soniya)
NIGHT_SECONDS = 45        # tungi harakat uchun vaqt
DAY_VOTE_SECONDS = 45     # kunduzgi ovoz berish uchun vaqt
