import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔍 Проверка: если токен не найден — выведем ошибку
if not BOT_TOKEN:
    raise RuntimeError(
        "❌ BOT_TOKEN не найден!\n"
        "1. Проверьте Railway → Variables → BOT_TOKEN\n"
        "2. Убедитесь, что нет пробелов до/после токена\n"
        "3. Перезапустите деплой после изменения Variables"
    )
