# Telegram Movie Bot

## 1. Kompyuterda ishga tushirish (test uchun)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python bot.py
```

`data/.env` faylida `BOT_TOKEN` va `ADMIN_ID` bo'lishi kerak.

## 2. 24/7 ishlashi uchun — GitHub + Railway orqali deploy

### 2.1. GitHub'ga yuklash

1. https://github.com da hisob oching (bepul)
2. Yangi bo'sh repository yarating (masalan `movie-bot`), Public yoki Private — farqi yo'q
3. VS Code terminalida, loyiha papkasida (`TelegramMovieBot` ichida):

```bash
git init
git add .
git commit -m "Birinchi versiya"
git branch -M main
git remote add origin https://github.com/FOYDALANUVCHI_NOMI/movie-bot.git
git push -u origin main
```

(`FOYDALANUVCHI_NOMI/movie-bot` o'rniga o'zingiz yaratgan repo manzilini qo'ying — GitHub sahifasida "...or push an existing repository" bo'limida bu buyruqlar tayyor holda ko'rsatiladi)

Eslatma: `.gitignore` fayli tokeningizni (`data/.env`) va bazani (`data/movies.db`) avtomatik GitHub'ga yubormaydi — bu xavfsizlik uchun to'g'ri.

### 2.2. Railway'da deploy qilish

1. https://railway.app ga GitHub hisobingiz bilan kiring
2. New Project -> Deploy from GitHub repo -> yuqorida yaratgan repo'ni tanlang
3. Loyiha ochilgach, Variables bo'limiga o'ting va qo'shing:
   - `BOT_TOKEN` = botingiz tokeni
   - `ADMIN_ID` = sizning Telegram ID'ingiz
4. Settings -> Deploy bo'limida Start Command avtomatik Procfile'dan olinadi (`python bot.py`) — qo'shimcha sozlash shart emas
5. Muhim: Volume qo'shing (bazangiz o'chib qolmasligi uchun):
   - Loyiha sahifasida "+ New" -> Volume
   - Mount path sifatida `/app/data` yozing
   - Shu bilan `movies.db` fayli har safar qayta deploy qilinganda ham saqlanib qoladi
6. Deploy tugagach, Railway loglarida "Polling started" yoki shunga o'xshash xabar chiqsa — bot ishga tushgan bo'ladi. Telegram'da botga `/start` yozib tekshiring.

### 2.3. Kodni yangilaganda

```bash
git add .
git commit -m "Yangilanish tavsifi"
git push
```

Railway buni avtomatik ko'rib, botni qayta deploy qiladi (Auto Deploy default holda yoqilgan).

## Eslatma

- `.env` faylni hech qachon GitHub'ga push qilmang — u tokeningizni oshkor qiladi
- Agar token oshkor bo'lib qolsa, darhol @BotFather orqali "Revoke current token" qiling
