# Mafia Bot — 1-bosqich (skelet)

## Tuzilma
```
mafia_bot/
├── main.py              # botni ishga tushiruvchi fayl
├── config.py             # .env dan sozlamalarni o'qiydi
├── database/
│   ├── postgres.py       # Neon PostgreSQL: users, groups, group_members
│   └── redis_db.py       # Upstash Redis: faol o'yin holati (chat_id bo'yicha)
├── handlers/
│   ├── private.py        # /start, /profile, /shop, /olmos + tungi tugmalar
│   ├── group.py          # /game, /start, /roles, /leave, /stop + kunduzgi ovoz
│   └── game_logic.py     # lobbi, rol taqsimoti, tun/kun sikli
├── keyboards/
│   └── inline.py         # lobbi va o'yinchi tanlash tugmalari
└── states/
    └── game_states.py    # Phase, Role enumlari va rol tavsiflari
```

## Mahalliy ishga tushirish
1. `.env.example` faylini `.env` deb nusxalang va to'ldiring:
   - `BOT_TOKEN` — @BotFather'dan
   - `DATABASE_URL` — Neon PostgreSQL connection string
   - `REDIS_URL` — Upstash Redis connection string (rediss://...)
2. `pip install -r requirements.txt --break-system-packages`
3. `python main.py`

## Railway'ga joylash
1. Repository'ni GitHub'ga push qiling.
2. Railway'da yangi loyiha yarating, GitHub repo'ni ulang.
3. Railway → Variables bo'limiga `BOT_TOKEN`, `DATABASE_URL`, `REDIS_URL` qo'shing.
4. Start command: `python main.py` (Railway odatda avtomatik aniqlaydi).

## 1-bosqichda nima bor
- 4 ta klassik rol: Tinch axoli, Mafia, Komissar Katani, Shifokor
- To'liq tungi/kunduzgi sikl: lobbi → rol taqsimoti → tun (mafia/doktor/komissar harakati) → kun (ovoz berish) → g'alabani tekshirish
- PostgreSQL orqali foydalanuvchi profili (pul, olmos, g'alaba, o'yinlar soni)
- Redis orqali har bir guruh uchun alohida o'yin holati

## Keyingi bosqichlarda qo'shiladi
- Qolgan standart va Golden Set rollar
- Do'kon/profil to'liq ishlashi (to'lov tizimi bilan)
- VIP guruh tizimi, /utag, /music, /love, /friends
- Admin panel, kredit tizimi, top guruhlar
