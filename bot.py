
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
import random
import aiosqlite

TOKEN = "7776073776:AAFFQldws5uyyMYG3ORAVanaazy41D5SZPE"
ADMIN_IDS = [6505085514]  # Замените на свой Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных
DB_NAME = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 1000,
            inventory TEXT DEFAULT ''
        )
        """)
        await db.commit()

# Команда /start
@dp.message(Command("start"))
async def start(message: Message):
    await add_user(message.from_user.id)
    await message.answer("👋 Добро пожаловать в Эконом Бот! Тут можно крутить рулетку, собирать предметы и многое другое. Напиши /menu")

# Главное меню
@dp.message(Command("menu"))
async def menu(message: Message):
    kb = [
        [types.KeyboardButton(text="🎰 Казино")],
        [types.KeyboardButton(text="🎒 Инвентарь")]
    ]
    await message.answer("📋 Меню:", reply_markup=types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# Казино рулетка
@dp.message(F.text == "🎰 Казино")
async def casino(message: Message):
    uid = message.from_user.id
    balance = await get_balance(uid)
    if balance < 100:
        return await message.answer("💸 У тебя не хватает 100 монет для ставки!")

    await update_balance(uid, -100)
    outcome = random.choices(["Выигрыш", "Ничья", "Проигрыш"], [0.2, 0.3, 0.5])[0]

    if outcome == "Выигрыш":
        await update_balance(uid, 300)
        await message.answer("🎉 Ты выиграл 300 монет!")
    elif outcome == "Ничья":
        await update_balance(uid, 100)
        await message.answer("😐 Ничья. Ставка возвращена.")
    else:
        await message.answer("😵 Ты проиграл 100 монет. Попробуй ещё раз!")

# Инвентарь
@dp.message(F.text == "🎒 Инвентарь")
async def inventory(message: Message):
    uid = message.from_user.id
    inv = await get_inventory(uid)
    text = "📦 Твой инвентарь пуст." if not inv else f"🎁 Предметы: {inv}"
    await message.answer(text)

# Админка
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Нет доступа.")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать монеты", callback_data="give_money")],
        [InlineKeyboardButton(text="🎁 Выдать предмет", callback_data="give_item")]
    ])
    await message.answer("🛠 Админ-панель:", reply_markup=kb)

# Обработка инлайн-кнопок
@dp.callback_query()
async def admin_buttons(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return await callback.answer("Нет доступа", show_alert=True)

    if callback.data == "give_money":
        await callback.message.answer("Введите ID пользователя и сумму через пробел.")
    elif callback.data == "give_item":
        await callback.message.answer("Введите ID пользователя и название предмета через пробел.")
    await callback.answer()

# Админ команды (выдача денег и предметов)
@dp.message(F.text.regexp(r"^\d+\s+\w+"))
async def admin_give(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        uid, value = message.text.strip().split()
        uid = int(uid)
        if value.isdigit():
            await update_balance(uid, int(value))
            await message.answer(f"💸 Пользователю {uid} выдано {value} монет.")
        else:
            await add_item(uid, value)
            await message.answer(f"🎁 Пользователю {uid} выдан предмет: {value}.")
    except:
        await message.answer("⚠ Ошибка обработки команды.")

# === БД функции ===
async def add_user(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users(user_id) VALUES (?)", (user_id,))
        await db.commit()

async def get_balance(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def update_balance(user_id, amount):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        await db.commit()

async def get_inventory(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT inventory FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""

async def add_item(user_id, item):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT inventory FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            inv = row[0] if row else ""
        new_inv = inv + ", " + item if inv else item
        await db.execute("UPDATE users SET inventory = ? WHERE user_id = ?", (new_inv, user_id))
        await db.commit()

# Запуск
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
