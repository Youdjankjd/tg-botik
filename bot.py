import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
ADMIN_IDS = [6505085514]  # замените на ваш Telegram ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

DB_NAME = "bot.db"

# --- Кнопки ---
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add("\U0001F4B0 Баланс", "\U0001F3B0 Казино", "\U0001F4B8 Рулетка")
main_kb.add("\U0001F6D2 Магазин", "\U0001F4BC Работа", "\U0001F4E6 Инвентарь")
main_kb.add("\U0001F451 ТОП", "\U0001F465 Рефералы")

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

# --- Команды ---
@dp.message_handler(commands=["start"])
async def start_cmd(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute_fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not user:
            ref = msg.get_args()
            ref_id = int(ref) if ref.isdigit() else None
            await db.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, ref_id))
            if ref_id:
                await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
            await db.commit()
    await msg.answer("Добро пожаловать в экономическую игру!", reply_markup=main_kb)

@dp.message_handler(lambda m: m.text == "\U0001F4B0 Баланс")
async def balance(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute_fetchone("SELECT balance, vip, mod FROM users WHERE user_id = ?", (user_id,))
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
        user = await db.execute_fetchone("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
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
        user = await db.execute_fetchone("SELECT balance FROM users WHERE user_id = ?", (user_id,))
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
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())


