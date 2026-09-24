import asyncpg

from config import DATABASE_URL

_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """Dastur ishga tushganda bir marta chaqiriladi: connection pool ochadi va jadvallarni yaratadi."""
    global _pool
    _pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=10)
    await _create_tables()


async def close_pool() -> None:
    if _pool:
        await _pool.close()


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Postgres pool hali ochilmagan. init_pool() ni chaqiring.")
    return _pool


async def _create_tables() -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                money BIGINT NOT NULL DEFAULT 0,
                diamonds BIGINT NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                games_played INTEGER NOT NULL DEFAULT 0,
                active_role TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS groups (
                chat_id BIGINT PRIMARY KEY,
                title TEXT,
                vip_until TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );

            CREATE TABLE IF NOT EXISTS group_members (
                chat_id BIGINT NOT NULL REFERENCES groups(chat_id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (chat_id, user_id)
            );
            """
        )


# ---------------------------------------------------------------------------
# Foydalanuvchilar bilan ishlash
# ---------------------------------------------------------------------------
async def ensure_user(user_id: int, username: str | None) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (user_id, username)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
            """,
            user_id,
            username,
        )


async def get_user(user_id: int) -> asyncpg.Record | None:
    async with _pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)


async def add_money(user_id: int, amount: int) -> None:
    async with _pool.acquire() as conn:
        await conn.execute("UPDATE users SET money = money + $2 WHERE user_id = $1", user_id, amount)


async def add_diamonds(user_id: int, amount: int) -> None:
    async with _pool.acquire() as conn:
        await conn.execute("UPDATE users SET diamonds = diamonds + $2 WHERE user_id = $1", user_id, amount)


async def record_game_result(user_id: int, won: bool) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET games_played = games_played + 1,
                wins = wins + $2
            WHERE user_id = $1
            """,
            user_id,
            1 if won else 0,
        )


# ---------------------------------------------------------------------------
# Guruhlar bilan ishlash
# ---------------------------------------------------------------------------
async def ensure_group(chat_id: int, title: str | None) -> None:
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO groups (chat_id, title)
            VALUES ($1, $2)
            ON CONFLICT (chat_id) DO UPDATE SET title = EXCLUDED.title
            """,
            chat_id,
            title,
        )


async def register_group_member(chat_id: int, user_id: int) -> None:
    """/utag uchun: guruhda faol bo'lgan foydalanuvchilarni saqlab boradi."""
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO group_members (chat_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT (chat_id, user_id) DO UPDATE SET last_seen = now()
            """,
            chat_id,
            user_id,
        )


async def get_group_members(chat_id: int) -> list[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetch(
            """
            SELECT u.user_id, u.username
            FROM group_members gm
            JOIN users u ON u.user_id = gm.user_id
            WHERE gm.chat_id = $1
            ORDER BY gm.last_seen DESC
            """,
            chat_id,
        )
