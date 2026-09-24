from enum import StrEnum


class Phase(StrEnum):
    """O'yinning joriy fazasi."""
    LOBBY = "lobby"        # o'yinchilar yig'ilmoqda
    NIGHT = "night"        # tungi harakatlar
    DAY_VOTE = "day_vote"  # kunduzgi ovoz berish
    FINISHED = "finished"  # o'yin tugadi


class Role(StrEnum):
    """1-bosqich uchun 4 ta klassik rol."""
    VILLAGER = "villager"      # Tinch axoli
    MAFIA = "mafia"            # Mafia/Don
    KOMISSAR = "komissar"      # Komissar Katani
    DOKTOR = "doktor"          # Shifokor


ROLE_NAMES_UZ = {
    Role.VILLAGER: "🧑 Tinch axoli",
    Role.MAFIA: "🕴 Mafia",
    Role.KOMISSAR: "🕵️ Komissar Katani",
    Role.DOKTOR: "👨‍⚕️ Shifokor",
}

ROLE_DESCRIPTIONS_UZ = {
    Role.VILLAGER: "Sizning vazifangiz — mafiani topish va ovoz berish jarayonida ularni osish.",
    Role.MAFIA: "Kechasi sherikligizda bitta o'yinchini yo'q qilasiz.",
    Role.KOMISSAR: "Kechasi bitta o'yinchini tekshirib, u mafiami-yo'qmi bilib olasiz.",
    Role.DOKTOR: "Kechasi bitta o'yinchini tanlab, uni o'limdan saqlaysiz (o'zingizni ham davolashingiz mumkin).",
}


def build_role_list(player_count: int) -> list[Role]:
    """O'yinchilar soniga qarab rollar ro'yxatini tuzadi (1-bosqich: sodda nisbat).

    4 ta o'yinchigacha: 1 mafia, 1 komissar, 1 doktor, qolgani tinch axoli.
    Har qo'shimcha 4 o'yinchiga yana 1 mafia qo'shiladi.
    """
    if player_count < 4:
        raise ValueError("Kamida 4 o'yinchi kerak.")

    mafia_count = max(1, player_count // 4)
    roles = [Role.MAFIA] * mafia_count + [Role.KOMISSAR, Role.DOKTOR]
    roles += [Role.VILLAGER] * (player_count - len(roles))
    return roles
