from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from database import postgres
from handlers import game_logic

router = Router()
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def cmd_start(message: Message):
    await postgres.ensure_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        "👋 Assalomu alaykum! Mafia o'yin botiga xush kelibsiz.\n\n"
        "Meni guruhingizga qo'shib, /game buyrug'i bilan o'yinni boshlashingiz mumkin.\n\n"
        "👤 /profile — profilingiz\n"
        "🛍 /shop — do'kon\n"
        "💎 /olmos — olmos sotib olish"
    )


@router.message(Command("profile"))
async def cmd_profile(message: Message):
    await postgres.ensure_user(message.from_user.id, message.from_user.full_name)
    user = await postgres.get_user(message.from_user.id)
    win_rate = f"{(user['wins'] / user['games_played'] * 100):.0f}%" if user["games_played"] else "0%"
    await message.answer(
        "👤 Profil\n\n"
        f"💵 Pul: {user['money']}\n"
        f"💎 Olmos: {user['diamonds']}\n\n"
        f"🎯 G'alaba: {user['wins']}\n"
        f"🎲 Barcha o'yinlar: {user['games_played']} ({win_rate})\n"
        f"🎭 Faol rol: {user['active_role'] or 'Yoq'}"
    )


@router.message(Command("shop"))
async def cmd_shop(message: Message):
    await message.answer(
        "🛍 Do'kon\n\n"
        "📁 Hujjatlar — 200 💵 (rolni tekshirishdan himoya)\n"
        "🛡 Himoya — 300 💵 (bir marta hayotni saqlaydi)\n"
        "⚖️ Ovozdan himoya — 1 💎 (osishdan bir marta qutqaradi)\n"
        "🥷 Geroy — 80 💎 (tong vaqtida ham otish imkoni)\n"
        "🔰 Geroydan himoya — 3 💎\n"
        "⭐️ VIP — 30 💎 dan (30 kun, komissiyasiz)\n\n"
        "(To'lov tizimi keyingi bosqichda ulanadi.)"
    )


@router.message(Command("olmos"))
async def cmd_olmos(message: Message):
    await message.answer(
        "💎 Olmos sotib olish\n\n"
        "Stars orqali:\n"
        "1 💎 — ⭐️5   |   15 💎 — ⭐️80\n"
        "40 💎 — ⭐️190  |  80 💎 — ⭐️430\n"
        "260 💎 — ⭐️1200 | 1000 💎 — ⭐️5000\n\n"
        "(To'lov tizimi keyingi bosqichda ulanadi.)"
    )


# ---------------------------------------------------------------------------
# Tungi harakat tugmalari (bot tomonidan shaxsiy chatga yuboriladi)
# callback_data format: "<action>:<group_chat_id>:<target_uid>"
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("night_mafia:"))
async def cb_night_mafia(callback: CallbackQuery):
    _, chat_id_str, target_id_str = callback.data.split(":")
    await game_logic.register_night_action(int(chat_id_str), "night_mafia", callback.from_user.id, int(target_id_str))
    await callback.answer("Tanlovingiz qabul qilindi.")
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("night_doktor:"))
async def cb_night_doktor(callback: CallbackQuery):
    _, chat_id_str, target_id_str = callback.data.split(":")
    await game_logic.register_night_action(int(chat_id_str), "night_doktor", callback.from_user.id, int(target_id_str))
    await callback.answer("Tanlovingiz qabul qilindi.")
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("night_komissar:"))
async def cb_night_komissar(callback: CallbackQuery):
    _, chat_id_str, target_id_str = callback.data.split(":")
    await game_logic.register_night_action(int(chat_id_str), "night_komissar", callback.from_user.id, int(target_id_str))
    await callback.answer("Tanlovingiz qabul qilindi.")
    await callback.message.edit_reply_markup(reply_markup=None)
