import asyncio
import random

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from config import DAY_VOTE_SECONDS, LOBBY_SECONDS, MIN_PLAYERS, NIGHT_SECONDS
from database import postgres, redis_db
from keyboards.inline import lobby_keyboard, player_choice_keyboard
from states.game_states import ROLE_DESCRIPTIONS_UZ, ROLE_NAMES_UZ, Phase, Role, build_role_list

# Har bir guruhdagi faol o'yin uchun background task (davom etayotganini kuzatish uchun)
_running_games: dict[int, asyncio.Task] = {}


# ---------------------------------------------------------------------------
# Lobbi (o'yinchilarni yig'ish)
# ---------------------------------------------------------------------------
async def start_lobby(bot: Bot, chat_id: int, admin_id: int) -> None:
    existing = await redis_db.load_game_state(chat_id)
    if existing and existing["phase"] != Phase.FINISHED:
        await bot.send_message(chat_id, "⚠️ Bu guruhda allaqachon o'yin ketmoqda.")
        return

    state = {
        "phase": Phase.LOBBY,
        "admin_id": admin_id,
        "players": {},          # {user_id_str: {"name": str, "role": None, "alive": True}}
        "day_number": 0,
        "night_actions": {},
        "day_votes": {},
    }
    await redis_db.save_game_state(chat_id, state)

    msg = await bot.send_message(
        chat_id,
        "🎮 Ro'yxatdan o'tish boshlandi!\n\nQo'shilish uchun pastdagi tugmani bosing.\n\n"
        f"Jami: 0 ta (kamida {MIN_PLAYERS} ta kerak)",
        reply_markup=lobby_keyboard(),
    )
    state["lobby_message_id"] = msg.message_id
    await redis_db.save_game_state(chat_id, state)

    task = asyncio.create_task(_lobby_timeout(bot, chat_id))
    _running_games[chat_id] = task


async def _lobby_timeout(bot: Bot, chat_id: int) -> None:
    await asyncio.sleep(LOBBY_SECONDS)
    await try_start_game(bot, chat_id)


async def add_player(bot: Bot, chat_id: int, user_id: int, name: str) -> str:
    """Lobbiga o'yinchi qo'shadi. Natija: 'added' | 'already' | 'no_lobby'."""
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.LOBBY:
        return "no_lobby"

    uid = str(user_id)
    if uid in state["players"]:
        return "already"

    state["players"][uid] = {"name": name, "role": None, "alive": True}
    await redis_db.save_game_state(chat_id, state)

    await postgres.ensure_user(user_id, name)
    await postgres.register_group_member(chat_id, user_id)

    count = len(state["players"])
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=state["lobby_message_id"],
            text=(
                "🎮 Ro'yxatdan o'tish boshlandi!\n\nQo'shilish uchun pastdagi tugmani bosing.\n\n"
                f"Jami: {count} ta (kamida {MIN_PLAYERS} ta kerak)"
            ),
            reply_markup=lobby_keyboard(),
        )
    except Exception:
        pass  # xabar o'zgarmagan bo'lsa aiogram xato beradi, uni e'tiborsiz qoldiramiz

    return "added"


async def try_start_game(bot: Bot, chat_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.LOBBY:
        return

    if len(state["players"]) < MIN_PLAYERS:
        await bot.send_message(chat_id, "❗ Yetarli odam bo'lmagani uchun o'yin to'xtatildi.")
        await redis_db.delete_game_state(chat_id)
        _running_games.pop(chat_id, None)
        return

    await _assign_roles(bot, chat_id, state)
    task = asyncio.create_task(_game_loop(bot, chat_id))
    _running_games[chat_id] = task


async def force_start(bot: Bot, chat_id: int, requester_id: int) -> None:
    """Admin /start bilan lobbini muddatidan oldin boshlaydi."""
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.LOBBY:
        await bot.send_message(chat_id, "⚠️ Hozir faol ro'yxatdan o'tish yo'q.")
        return
    if requester_id != state["admin_id"]:
        await bot.send_message(chat_id, "⛔️ Faqat o'yinni boshlagan admin buni qila oladi.")
        return

    old_task = _running_games.pop(chat_id, None)
    if old_task:
        old_task.cancel()
    await try_start_game(bot, chat_id)


# ---------------------------------------------------------------------------
# Rollarni taqsimlash
# ---------------------------------------------------------------------------
async def _assign_roles(bot: Bot, chat_id: int, state: dict) -> None:
    player_ids = list(state["players"].keys())
    roles = build_role_list(len(player_ids))
    random.shuffle(roles)

    for uid, role in zip(player_ids, roles):
        state["players"][uid]["role"] = role.value

    state["phase"] = Phase.NIGHT
    state["day_number"] = 1
    await redis_db.save_game_state(chat_id, state)

    await bot.send_message(
        chat_id,
        "✅ Ro'yxatdan o'tish yakunlandi! Bir necha soniyada har biringizga shaxsiy xabar orqali rolingiz yuboriladi.",
    )

    for uid, info in state["players"].items():
        role = Role(info["role"])
        text = (
            f"Siz — {ROLE_NAMES_UZ[role]}!\n\n"
            f"{ROLE_DESCRIPTIONS_UZ[role]}"
        )
        try:
            await bot.send_message(int(uid), text)
        except TelegramForbiddenError:
            # o'yinchi botni bloklagan — uni o'yindan chiqaramiz
            info["alive"] = False
    await redis_db.save_game_state(chat_id, state)


# ---------------------------------------------------------------------------
# Tun / kun sikli
# ---------------------------------------------------------------------------
async def _game_loop(bot: Bot, chat_id: int) -> None:
    while True:
        state = await redis_db.load_game_state(chat_id)
        if not state:
            return

        await _run_night(bot, chat_id)
        winner = await _check_win(chat_id)
        if winner:
            await _finish_game(bot, chat_id, winner)
            return

        await _run_day(bot, chat_id)
        winner = await _check_win(chat_id)
        if winner:
            await _finish_game(bot, chat_id, winner)
            return


async def _run_night(bot: Bot, chat_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    state["phase"] = Phase.NIGHT
    state["night_actions"] = {}
    await redis_db.save_game_state(chat_id, state)

    await bot.send_message(
        chat_id,
        f"🌙 {state['day_number']}-kecha tushdi. Ko'chaga faqat jasur va qo'rqmas odamlar chiqishdi.\n"
        "Maxsus rolga ega o'yinchilar shaxsiy xabarda harakat qilishmoqda...",
    )

    players = state["players"]
    for uid, info in players.items():
        if not info["alive"]:
            continue
        role = Role(info["role"])
        if role == Role.MAFIA:
            kb = player_choice_keyboard("night_mafia", players, chat_id, exclude_user_id=int(uid))
            if kb.inline_keyboard:
                await _safe_send(bot, int(uid), "🕴 Bu kecha kimni yo'q qilamiz?", kb)
        elif role == Role.DOKTOR:
            kb = player_choice_keyboard("night_doktor", players, chat_id)
            if kb.inline_keyboard:
                await _safe_send(bot, int(uid), "👨‍⚕️ Bu kecha kimni davolaysiz?", kb)
        elif role == Role.KOMISSAR:
            kb = player_choice_keyboard("night_komissar", players, chat_id, exclude_user_id=int(uid))
            if kb.inline_keyboard:
                await _safe_send(bot, int(uid), "🕵️ Bu kecha kimni tekshiramiz?", kb)

    await asyncio.sleep(NIGHT_SECONDS)
    await _resolve_night(bot, chat_id)


async def _safe_send(bot: Bot, user_id: int, text: str, kb) -> None:
    try:
        await bot.send_message(user_id, text, reply_markup=kb)
    except TelegramForbiddenError:
        pass


async def register_night_action(chat_id: int, action: str, actor_id: int, target_id: int) -> None:
    """action: 'night_mafia' | 'night_doktor' | 'night_komissar'."""
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.NIGHT:
        return
    state["night_actions"][action] = target_id
    await redis_db.save_game_state(chat_id, state)


async def _resolve_night(bot: Bot, chat_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.NIGHT:
        return

    actions = state["night_actions"]
    mafia_target = actions.get("night_mafia")
    doktor_target = actions.get("night_doktor")
    komissar_target = actions.get("night_komissar")

    victim_text = "😴 Bu kecha hech kim o'lmadi."
    if mafia_target is not None and mafia_target != doktor_target:
        uid = str(mafia_target)
        if uid in state["players"] and state["players"][uid]["alive"]:
            state["players"][uid]["alive"] = False
            victim_text = f"☠️ {state['players'][uid]['name']} vahshiylarcha o'ldirildi."

    # Komissar natijasi — faqat o'ziga
    if komissar_target is not None:
        target_uid = str(komissar_target)
        target_info = state["players"].get(target_uid)
        if target_info:
            is_mafia = target_info["role"] == Role.MAFIA.value
            result = "u MAFIA ekan! 🔴" if is_mafia else "u tinch fuqaro ekan. 🟢"
            komissar_uid = next(
                (uid for uid, info in state["players"].items() if info["role"] == Role.KOMISSAR.value),
                None,
            )
            if komissar_uid:
                await _safe_send(bot, int(komissar_uid), f"🕵️ Tekshiruv natijasi: {result}", None)

    state["phase"] = Phase.DAY_VOTE
    await redis_db.save_game_state(chat_id, state)
    await bot.send_message(chat_id, f"☀️ {state['day_number']}-kun keldi.\n\n{victim_text}")


# ---------------------------------------------------------------------------
# Kunduzgi ovoz berish
# ---------------------------------------------------------------------------
async def _run_day(bot: Bot, chat_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    state["day_votes"] = {}
    await redis_db.save_game_state(chat_id, state)

    alive = {uid: info for uid, info in state["players"].items() if info["alive"]}
    names = "\n".join(f"• {info['name']}" for info in alive.values())
    kb = player_choice_keyboard("day_vote", state["players"], chat_id)

    await bot.send_message(
        chat_id,
        f"🗳 Tirik o'yinchilar:\n{names}\n\nKimni osishga ovoz berasiz? ({DAY_VOTE_SECONDS} soniya)",
        reply_markup=kb,
    )

    await asyncio.sleep(DAY_VOTE_SECONDS)
    await _resolve_day_vote(bot, chat_id)


async def register_day_vote(chat_id: int, voter_id: int, target_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.DAY_VOTE:
        return
    if not state["players"].get(str(voter_id), {}).get("alive"):
        return
    state["day_votes"][str(voter_id)] = target_id
    await redis_db.save_game_state(chat_id, state)


async def _resolve_day_vote(bot: Bot, chat_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    if not state or state["phase"] != Phase.DAY_VOTE:
        return

    tally: dict[int, int] = {}
    for target_id in state["day_votes"].values():
        tally[target_id] = tally.get(target_id, 0) + 1

    if tally:
        max_votes = max(tally.values())
        top = [uid for uid, votes in tally.items() if votes == max_votes]
    else:
        top = []

    if len(top) == 1:
        uid = str(top[0])
        if state["players"].get(uid, {}).get("alive"):
            state["players"][uid]["alive"] = False
            await bot.send_message(chat_id, f"⚖️ {state['players'][uid]['name']} ovoz bilan osildi.")
    else:
        await bot.send_message(chat_id, "🤝 Ovozlar durrang bo'ldi — bugun hech kim osilmaydi.")

    state["day_number"] += 1
    await redis_db.save_game_state(chat_id, state)


# ---------------------------------------------------------------------------
# G'alabani tekshirish va o'yinni yakunlash
# ---------------------------------------------------------------------------
async def _check_win(chat_id: int) -> str | None:
    state = await redis_db.load_game_state(chat_id)
    if not state:
        return None

    alive = [info for info in state["players"].values() if info["alive"]]
    mafia_alive = sum(1 for info in alive if info["role"] == Role.MAFIA.value)
    town_alive = len(alive) - mafia_alive

    if mafia_alive == 0:
        return "town"
    if mafia_alive >= town_alive:
        return "mafia"
    return None


async def _finish_game(bot: Bot, chat_id: int, winner: str) -> None:
    state = await redis_db.load_game_state(chat_id)
    state["phase"] = Phase.FINISHED
    await redis_db.save_game_state(chat_id, state)

    winner_text = "🧑 Tinch aholi" if winner == "town" else "🕴 Mafia"
    lines = [f"🏁 O'yin tugadi!\nG'olib: {winner_text}\n"]

    for uid, info in state["players"].items():
        role = Role(info["role"])
        won = (winner == "town" and role != Role.MAFIA) or (winner == "mafia" and role == Role.MAFIA)
        lines.append(f"{'✅' if won else '❌'} {info['name']} — {ROLE_NAMES_UZ[role]}")
        await postgres.record_game_result(int(uid), won)
        if won:
            await postgres.add_money(int(uid), 20)

    await bot.send_message(chat_id, "\n".join(lines))
    await redis_db.delete_game_state(chat_id)
    _running_games.pop(chat_id, None)


async def cancel_game(bot: Bot, chat_id: int, requester_id: int) -> None:
    state = await redis_db.load_game_state(chat_id)
    if not state:
        await bot.send_message(chat_id, "⚠️ Hozir faol o'yin yo'q.")
        return
    if requester_id != state["admin_id"]:
        await bot.send_message(chat_id, "⛔️ Faqat o'yinni boshlagan admin uni to'xtata oladi.")
        return

    task = _running_games.pop(chat_id, None)
    if task:
        task.cancel()
    await redis_db.delete_game_state(chat_id)
    await bot.send_message(chat_id, "🛑 O'yin to'xtatildi.")
