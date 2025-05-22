import asyncio
import random
import time
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
ADMIN_IDS = [6505085514]
CHANNEL_USERNAME = "@economicbotlive"

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_NAME = "bot.db"

# --- Кнопки ---
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("\U0001F4B0 Баланс", "\U0001F3B0 Казино", "\U0001F4B8 Рулетка")
main_kb.add("\U0001F6D2 Магазин", "\U0001F4BC Работа", "\U0001F4E6 Инвентарь")
main_kb.add("\U0001F451 ТОП", "\U0001F465 Рефералы", "\U0001F381 Промокод")

# --- Инициализация БД ---
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                vip INTEGER DEFAULT 0,
                mod INTEGER DEFAULT 0,
                referrer INTEGER,
                referrals INTEGER DEFAULT 0,
                last_daily INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                user_id INTEGER,
                item_name TEXT,
                amount INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS promo (
                code TEXT PRIMARY KEY,
                amount INTEGER,
                activated INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# --- Проверка подписки ---
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "creator", "administrator"]
    except TelegramBadRequest:
        return False

# --- Старт ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id

    if not await check_subscription(user_id):
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [types.InlineKeyboardButton(text="🔄 Проверить", callback_data="check_sub")]
        ])
        await msg.answer("❗ Для использования бота подпишитесь на канал:", reply_markup=kb)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not await user.fetchone():
            await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            await db.commit()
    await msg.answer("Добро пожаловать в экономическую игру!", reply_markup=main_kb)

# --- Промокод ---
@dp.message(lambda m: m.text == "\U0001F381 Промокод")
async def promo_input(msg: types.Message):
    await msg.answer("Введите промокод:")

@dp.message(lambda m: m.text.startswith("!промо ") and m.from_user.id in ADMIN_IDS)
async def create_promo(msg: types.Message):
    try:
        _, code, amount = msg.text.split()
        amount = int(amount)
    except:
        await msg.answer("❌ Неверный формат. Используй: !промо <КОД> <СУММА>")
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO promo (code, amount) VALUES (?, ?)", (code.upper(), amount))
        await db.commit()
    await msg.answer(f"✅ Промокод {code.upper()} на {amount} монет создан.")

@dp.message(lambda m: True)
async def check_promo(msg: types.Message):
    user_id = msg.from_user.id
    code = msg.text.strip().upper()

    async with aiosqlite.connect(DB_NAME) as db:
        promo = await db.execute_fetchone("SELECT amount, activated FROM promo WHERE code = ?", (code,))
        if promo:
            if promo[1]:
                await msg.answer("⚠️ Этот промокод уже был активирован.")
            else:
                await db.execute("UPDATE promo SET activated = 1 WHERE code = ?", (code,))
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (promo[0], user_id))
                await db.commit()
                await msg.answer(f"🎉 Вы активировали промокод и получили {promo[0]} монет!")
        else:
            await msg.answer("❌ Неверный промокод.")

@dp.callback_query(lambda c: c.data == "check_sub")
async def recheck_subscription(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await callback.message.answer("✅ Спасибо за подписку!", reply_markup=main_kb)
    else:
        await callback.answer("❗ Вы ещё не подписаны.", show_alert=True)

# --- Запуск ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


