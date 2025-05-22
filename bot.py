import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
ADMIN_IDS = [6505085514]
CHANNEL_USERNAME = "economicbotlive"

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

DB_NAME = "bot.db"

# --- Кнопки ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="\U0001F4B0 Баланс"), KeyboardButton(text="\U0001F3B0 Казино"), KeyboardButton(text="\U0001F4B8 Рулетка")],
        [KeyboardButton(text="\U0001F6D2 Магазин"), KeyboardButton(text="\U0001F4BC Работа"), KeyboardButton(text="\U0001F4E6 Инвентарь")],
        [KeyboardButton(text="\U0001F451 ТОП"), KeyboardButton(text="\U0001F465 Рефералы")]
    ],
    resize_keyboard=True
)

subscribe_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="📢 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
    [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
])

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
        await db.commit()

# --- Проверка подписки ---
async def is_subscribed(user_id):
    member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
    return member.status in ("member", "administrator", "creator")

@dp.message(F.text, Command("start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id

    if not await is_subscribed(user_id):
        await msg.answer("🔒 Чтобы пользоваться ботом, подпишитесь на наш канал!", reply_markup=subscribe_kb)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        ref = msg.get_args()
        ref_id = int(ref) if ref.isdigit() else None
        user = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not await user.fetchone():
            await db.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, ref_id))
            if ref_id:
                await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
            await db.commit()
    await msg.answer("Добро пожаловать в экономическую игру!", reply_markup=main_kb)

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if await is_subscribed(user_id):
        await callback.message.edit_text("✅ Подписка подтверждена! Напишите /start.")
    else:
        await callback.answer("❌ Вы всё ещё не подписаны!", show_alert=True)

@dp.message_handler(lambda m: m.text == "\U0001F4B0 Баланс")
async def balance(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute("SELECT balance, vip, mod FROM users WHERE user_id = ?", (user_id,))
        user = await user.fetchone()
        if user:
            bal, vip, mod = user
            status = "VIP" if vip else "Обычный"
            if mod:
                status = "Модератор"
            await msg.answer(f"Ваш баланс: {bal} монет\nСтатус: {status}")
        else:
            await msg.answer("Вы не зарегистрированы. Напишите /start")

@dp.message_handler(lambda m: m.text == "\U0001F4B8 Рулетка")
async def roulette(msg: types.Message):
    import time
    user_id = msg.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        user = await user.fetchone()
        if user:
            last = user[0]
            if now - last < 86400:
                remain = 86400 - (now - last)
                hours = remain // 3600
                minutes = (remain % 3600) // 60
                await msg.answer(f"Вы уже получали рулетку. Подождите {hours} ч. {minutes} мин.")
                return
            amount = random.choices([0, 500, 1000, 2500, 5000], weights=[50, 25, 15, 8, 2])[0]
            await db.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (amount, now, user_id))
            await db.commit()
            await msg.answer(f"Вы выиграли {amount} монет в рулетке!")

@dp.message_handler(lambda m: m.text == "\U0001F3B0 Казино")
async def casino(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = await user.fetchone()
        if user and user[0] >= 100:
            win = random.random() < 0.25
            amount = 1000 if win else -100
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()
            text = "Вы выиграли 1000 монет!" if win else "Вы проиграли 100 монет."
            await msg.answer(text)
        else:
            await msg.answer("У вас недостаточно монет (нужно минимум 100).")

# --- Запуск ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



