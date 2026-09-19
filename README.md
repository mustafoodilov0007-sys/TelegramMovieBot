# 🎬 Kino Bot

## Ishga tushirish
1. Python 3.10+ o'rnating.
2. `pip install -r requirements.txt`
3. `.env.example` faylini `.env` deb nomlang va ichiga **BOT_TOKEN** (@BotFather) hamda **ADMINS** (o'zingizning Telegram ID, @userinfobot dan) yozing.
4. `python main.py`

## Admin panel
Botga `/admin` yozing yoki menyudagi **🛠 Admin panel** tugmasini bosing.

- **🎬 Kino qo'shish** (yoki `/add`) — video yuboring → nom → bo'lim. Bot avtomatik kod va havola beradi (`https://t.me/BOT?start=KOD`).
- **🗑 Kino o'chirish** — kod bo'yicha.
- **🔗 Majburiy kanallar** — kanal qo'shish/o'chirish. Bot kanalga **admin** bo'lishi shart.
- **✉️ Xabar yuborish** — barcha obunachilarga (matn/rasm/video).
- **📊 Statistika**, **👮 Adminlar**, **⚙️ Matnlar** (salomlashish, qo'llab-quvvatlash, reklama matni).

## Foydalanuvchi
Kod (`356`), nom (`Titanik`) yoki havola (`https://t.me/BOT?start=356`) yuborsa — kino chiqadi.

## Admin buyruqlari
`/add` — kino qo'shish, `/del` — kino o'chirish, `/stats` — statistika, `/channels` — majburiy kanallar, `/broadcast` — xabar yuborish, `/admin` — panel.

## Railway'da 24/7 ishlatish
1. Kompyuterdagi botni to'xtating (bir token bilan ikki joyda ishlamaydi).
2. Kodni GitHub'ga yuklang (`.env` yuklanmaydi — `.gitignore` himoya qiladi).
3. Railway → Variables: `BOT_TOKEN`, `ADMINS`.
4. Railway → Volume qo'shing, Mount path: `/data` (baza shu yerda saqlanadi, deployda o'chmaydi).
5. Settings → Start Command: `python main.py` (kerak bo'lsa).
6. Deploy logida `Bot ishga tushdi` chiqishini tekshiring.

## Backup
`/backup` — baza nusxasini yuboradi. `/restore` — nusxani qaytaradi.
