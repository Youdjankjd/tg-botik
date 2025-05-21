import asyncio
import logging
import os
import random
import aiosqlite

from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from fastapi import FastAPI, Request

# === Конфигурация ===
BOT_TOKEN = os.getenv("BOT_TOKEN", "7776073776:AAFTWIurr_tR6cxIx4GZ4iihD7rnpJ2gOyQ")  # Лучше хранить в .env или на Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://tg-botik.onrender.com")  # Render URL
ADMIN_IDS = [6505085514]  # Замени на свой Telegram ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Обработка команд ===
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🎉 Добро пожаловать в нашего телеграм-бота казино!")

# Пример рулетки (будет расширено)
@dp.message(Command("roulette"))
async def roulette(message: Message):
    result = random.choice(["🔴 Красное", "⚫ Чёрное", "🟢 Зеро"])
    await message.answer(f"🎰 Выпало: {result}")

# Пример админки
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🛠 Админ-панель:\n- /stats — статистика\n- /broadcast — рассылка")
    else:
        await message.answer("⛔ У вас нет доступа.")

# === Webhook (для Render) ===
app = FastAPI()

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook()
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    update = types.Update(**await request.json())
    await dp._process_update(update)
    return {"ok": True}

# === Локальный запуск (например, для тестов) ===
if __name__ == "__main__":
    import uvicorn
    asyncio.run(bot.delete_webhook())
    uvicorn.run("bot:app", host="0.0.0.0", port=8000)

