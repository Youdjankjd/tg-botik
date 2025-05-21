import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
import logging
import os

# Настрой логгирование
logging.basicConfig(level=logging.INFO)

# Токен бота
TOKEN = os.getenv("7776073776:AAFTWIurr_tR6cxIx4GZ4iihD7rnpJ2gOyQ") or "7776073776:AAFTWIurr_tR6cxIx4GZ4iihD7rnpJ2gOyQ"

# Создаем бота и диспетчер
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Простой хендлер
@dp.message()
async def echo_handler(message: Message):
    await message.answer(f"Ты написал: {message.text}")

# Основная функция запуска
async def main():
    logging.info("Бот запущен на Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


