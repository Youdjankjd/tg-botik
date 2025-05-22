import asyncio
import random
import time
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import F
from aiogram.client.default import DefaultBotProperties

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
ADMIN_IDS = [6505085514]
CHANNEL_ID = -1002123456789  # заменим позже на реальный ID канала, можно узнать через @userinfobot

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

DB_NAME = "bot.db"

# --- Кнопки ---
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎰 Казино"), KeyboardButton(text="💸 Рулетка")],
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="💼 Работа"), KeyboardButton(text="📦 Инвентарь")],
        [KeyboardButton(text="👑 ТОП"), KeyboardButton(text="👥 Рефералы")]
    ],
    resize_keyboard=True
)

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
            CREATE TABLE IF NOT EXISTS promocodes (
                code TEXT PRIMARY KEY,
                amount INTEGER
            )
        """)
        await db.commit()

# --- Подписка ---
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id="@economicbotlive", user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# --- Команды ---
@dp.message(Command("start"))
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    if not await check_subscription(user_id):
        await msg.answer("Пожалуйста, подпишитесь на канал: https://t.me/economicbotlive")
        return
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await cur.fetchone()
        if not user:
            ref = msg.text.split(" ")[-1] if " " in msg.text else None
            ref_id = int(ref) if ref and ref.isdigit() else None
            await db.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, ref_id))
            if ref_id:
                await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
            await db.commit()
    await msg.answer("Добро пожаловать в экономическую игру!", reply_markup=main_kb)

@dp.message(F.text == "💰 Баланс")
async def balance(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance, vip, mod FROM users WHERE user_id = ?", (user_id,))
        user = await cur.fetchone()
        if user:
            bal, vip, mod = user
            status = "Модератор" if mod else ("VIP" if vip else "Обычный")
            await msg.answer(f"Ваш баланс: {bal} монет\nСтатус: {status}")
        else:
            await msg.answer("Вы не зарегистрированы. Напишите /start")

@dp.message(F.text == "💸 Рулетка")
async def roulette(msg: types.Message):
    user_id = msg.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        user = await cur.fetchone()
        if user:
            last = user[0]
            if now - last < 86400:
                remain = 86400 - (now - last)
                await msg.answer(f"Вы уже получали рулетку. Подождите {remain // 3600} ч. {(remain % 3600) // 60} мин.")
                return
            amount = random.choices([0, 500, 1000, 2500, 5000], weights=[50, 25, 15, 8, 2])[0]
            await db.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (amount, now, user_id))
            await db.commit()
            await msg.answer(f"Вы выиграли {amount} монет в рулетке!")

@dp.message(F.text == "🎰 Казино")
async def casino(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        user = await cur.fetchone()
        if user and user[0] >= 100:
            win = random.random() < 0.25
            amount = 1000 if win else -100
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()
            text = "Вы выиграли 1000 монет!" if win else "Вы проиграли 100 монет."
            await msg.answer(text)
        else:
            await msg.answer("У вас недостаточно монет (нужно минимум 100).")

@dp.message(Command("promo"))
async def promo_handler(msg: types.Message):
    user_id = msg.from_user.id
    parts = msg.text.split()
    if len(parts) == 2:
        code = parts[1]
        async with aiosqlite.connect(DB_NAME) as db:
            cur = await db.execute("SELECT amount FROM promocodes WHERE code = ?", (code,))
            promo = await cur.fetchone()
            if promo:
                await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (promo[0], user_id))
                await db.commit()
                await msg.answer(f"Промокод активирован! Вы получили {promo[0]} монет.")
            else:
                await msg.answer("Неверный или уже использованный промокод.")
    else:
        await msg.answer("Используйте формат: /promo КОД")

@dp.message(Command("createpromo"))
async def create_promo(msg: types.Message):
    if msg.from_user.id not in ADMIN_IDS:
        return
    parts = msg.text.split()
    if len(parts) != 3:
        await msg.answer("Формат: /createpromo КОД СУММА")
        return
    code, amount = parts[1], int(parts[2])
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO promocodes (code, amount) VALUES (?, ?)", (code, amount))
        await db.commit()
        await msg.answer(f"Промокод {code} создан на сумму {amount} монет.")

# --- Запуск ---
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



