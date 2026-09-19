from dotenv import load_dotenv
import os

load_dotenv("data/.env")

BOT_TOKEN = os.getenv("8898088704:AAF7ykAPOrMGZlMWgbR_GPLlX6HfI-hiEaQ")
ADMIN_ID = int(os.getenv("7741577083", "0"))

# Majburiy obuna uchun kanal (masalan: @kanal_username yoki -100123456789)
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
# Foydalanuvchi bosadigan "Kanalga o'tish" tugmasi uchun havola
CHANNEL_URL = os.getenv("CHANNEL_URL", "")
