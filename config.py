from dotenv import load_dotenv
import os

load_dotenv("data/.env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Majburiy obuna uchun kanal (masalan: @kanal_username yoki -100123456789)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
# Foydalanuvchi bosadigan "Kanalga o'tish" tugmasi uchun havola
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
