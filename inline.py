from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def lobby_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🙋 Qo'shilish", callback_data="lobby_join")],
        ]
    )


def player_choice_keyboard(
    action: str,
    players: dict[str, dict],
    chat_id: int,
    exclude_user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """Tunda nishon tanlash (shaxsiy chatda) yoki kunduzi ovoz berish (guruhda) uchun tugmalar.

    action: "night_mafia" | "night_doktor" | "night_komissar" | "day_vote"
    players: {user_id_str: {"name": str, "alive": bool, ...}}
    chat_id: o'yin ketayotgan guruh id'si — tungi harakatlar shaxsiy chatdan kelgani uchun
             callback_data ichida qaysi o'yinga tegishli ekanini bilish uchun kerak.
    """
    buttons = []
    for uid_str, info in players.items():
        if not info.get("alive", True):
            continue
        if exclude_user_id is not None and int(uid_str) == exclude_user_id:
            continue
        buttons.append(
            [InlineKeyboardButton(text=info["name"], callback_data=f"{action}:{chat_id}:{uid_str}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def role_reveal_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Rolni ko'rish", url="https://t.me/")],  # botning username bilan almashtiriladi
        ]
    )
