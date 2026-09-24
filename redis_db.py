import json
from typing import Any

import redis.asyncio as redis

from config import REDIS_URL

_redis: redis.Redis | None = None


async def init_redis() -> None:
    global _redis
    _redis = redis.from_url(REDIS_URL, decode_responses=True)


async def close_redis() -> None:
    if _redis:
        await _redis.close()


def get_redis() -> redis.Redis:
    if _redis is None:
        raise RuntimeError("Redis hali ulanmagan. init_redis() ni chaqiring.")
    return _redis


def _game_key(chat_id: int) -> str:
    return f"game:{chat_id}"


async def save_game_state(chat_id: int, state: dict[str, Any]) -> None:
    """O'yin holatini (o'yinchilar, rollar, faza) chat_id bo'yicha JSON qilib Redis'ga yozadi."""
    await _redis.set(_game_key(chat_id), json.dumps(state))


async def load_game_state(chat_id: int) -> dict[str, Any] | None:
    raw = await _redis.get(_game_key(chat_id))
    if raw is None:
        return None
    return json.loads(raw)


async def delete_game_state(chat_id: int) -> None:
    await _redis.delete(_game_key(chat_id))
