from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import postgres, redis_db
from handlers import game_logic
from states.game_states import Phase, ROLE_DESCRIPTIONS_UZ, ROLE_NAMES_UZ

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))
router.callback_query.filter(F.message.chat.type.in_({"group", "supergroup"}))


def _display_name(message_or_user) -> str:
    user = message_or_user.from_user
    return user.full_name or user.username or str(user.id)


@router.message(Command("game"))
async def cmd_game(message: Message):
    await postgres.ensure_group(message.chat.id, message.chat.title)
    await postgres.ensure_user(message.from_user.id, _display_name(message))
    await game_logic.start_lobby(message.bot, message.chat.id, message.from_user.id)


@router.message(Command("start"))
async def cmd_force_start(message: Message):
    # Guruhda /start — lobbini muddatidan oldin boshlash (faqat admin)
    await game_logic.force_start(message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data == "lobby_join")
async def cb_lobby_join(callback: CallbackQuery):
    name = _display_name(callback)
    result = await game_logic.add_player(callback.bot, callback.message.chat.id, callback.from_user.id, name)
    if result == "added":
        await callback.answer("Siz o'yinga qo'shildingiz!")
    elif result == "already":
        await callback.answer("Siz allaqachon ro'yxatdasiz.")
    else:
        await callback.answer("Hozir ro'yxatdan o'tish faol emas.", show_alert=True)


@router.message(Command("roles"))
async def cmd_roles(message: Message):
    lines = ["🎭 Mavjud rollar ro'yxati:\n"]
    for role, name in ROLE_NAMES_UZ.items():
        lines.append(f"{name} — {ROLE_DESCRIPTIONS_UZ[role]}")
    await message.answer("\n".join(lines))


@router.message(Command("leave"))
async def cmd_leave(message: Message):
    state = await redis_db.load_game_state(message.chat.id)
    if not state or state["phase"] != Phase.LOBBY:
        await message.answer("⚠️ Hozir chiqib bo'ladigan faol ro'yxat yo'q.")
        return
    uid = str(message.from_user.id)
    if uid in state["players"]:
        del state["players"][uid]
        await redis_db.save_game_state(message.chat.id, state)
        await message.answer("🚪 Ro'yxatdan chiqdingiz.")
    else:
        await message.answer("Siz ro'yxatda yo'q edingiz.")


@router.message(Command("stop", "cancel"))
async def cmd_stop(message: Message):
    await game_logic.cancel_game(message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data.startswith("day_vote:"))
async def cb_day_vote(callback: CallbackQuery):
    # format: day_vote:<chat_id>:<target_uid>
    _, chat_id_str, target_id_str = callback.data.split(":")
    await game_logic.register_day_vote(int(chat_id_str), callback.from_user.id, int(target_id_str))
    await callback.answer("Ovozingiz qabul qilindi.")
