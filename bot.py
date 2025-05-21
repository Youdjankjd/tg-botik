import asyncio
import logging
import random
import aiosqlite
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder

TOKEN = "ТВОЙ_ТОКЕН"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DATABASE = "users.db"


async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 1000,
                vip INTEGER DEFAULT 0,
                admin INTEGER DEFAULT 0
            )
        """)
        await db.commit()


@dp.message(Command("start"))
async def start(message: Message):
    await register_user(message.from_user.id)
    await message.answer("👋 Добро пожаловать в казино-бот!")


async def register_user(user_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()


async def get_user(user_id):
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT balance, vip, admin FROM users WHERE user_id = ?", (user_id,))
        return await cursor.fetchone()


@dp.message(Command("balance"))
async def balance(message: Message):
    balance, vip, admin = await get_user(message.from_user.id)
    status = []
    if vip:
        status.append("🌟 VIP")
    if admin:
        status.append("🛠 Админ")
    status_text = ", ".join(status) if status else "Обычный пользователь"
    await message.answer(f"💰 Баланс: {balance} монет\nСтатус: {status_text}")


@dp.message(Command("roulette"))
async def roulette(message: Message):
    user_id = message.from_user.id
    balance, *_ = await get_user(user_id)
    if balance < 100:
        return await message.answer("❌ Недостаточно монет для игры. Нужна хотя бы 100 монет.")

    result = random.choice(["🔴", "⚫", "🟢"])
    win = result == "🟢"
    new_balance = balance + 500 if win else balance - 100

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        await db.commit()

    if win:
        await message.answer(f"{result} Поздравляем! Вы выиграли 500 монет!")
    else:
        await message.answer(f"{result} Увы, вы проиграли 100 монет.")


@dp.message(Command("buy_vip"))
async def buy_vip(message: Message):
    user_id = message.from_user.id
    balance, vip, _ = await get_user(user_id)
    if vip:
        return await message.answer("✅ У вас уже есть VIP-статус.")
    if balance < 100000:
        return await message.answer("❌ Недостаточно монет. Требуется 100000 монет.")

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET vip = 1, balance = balance - 100000 WHERE user_id = ?", (user_id,))
        await db.commit()
    await message.answer("🌟 Вы успешно приобрели VIP-статус!")


@dp.message(Command("buy_admin"))
async def buy_admin(message: Message):
    user_id = message.from_user.id
    balance, _, admin = await get_user(user_id)
    if admin:
        return await message.answer("✅ Вы уже админ.")
    if balance < 100000000:
        return await message.answer("❌ Недостаточно монет. Требуется 100000000 монет.")

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE users SET admin = 1, balance = balance - 100000000 WHERE user_id = ?", (user_id,))
        await db.commit()
    await message.answer("🛠 Вы стали админом!")


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())



