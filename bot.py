import asyncio
import sqlite3
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.utils.markdown import hbold
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.methods import GetChatMember

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
CHANNEL_ID = "@economicbotlive"
ADMIN_IDS = [6505085514] 

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML, session=AiohttpSession())
dp = Dispatcher()

# Настройка логов
logging.basicConfig(level=logging.INFO)

# SQLite
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    referrer INTEGER,
    referrals INTEGER DEFAULT 0
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    income INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS inventory (
    user_id INTEGER,
    item_id INTEGER,
    count INTEGER DEFAULT 0,
    FOREIGN KEY(item_id) REFERENCES items(id)
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS promo (
    code TEXT PRIMARY KEY,
    reward INTEGER
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    reward INTEGER
)""")

conn.commit()

# Клавиатура
def main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🏆 Топ", callback_data="top")],
        [InlineKeyboardButton(text="🛍 Магазин", callback_data="shop")],
        [InlineKeyboardButton(text="💼 Работа", callback_data="work")],
        [InlineKeyboardButton(text="🎁 Промокод", callback_data="promo")],
        [InlineKeyboardButton(text="🎒 Инвентарь", callback_data="inventory")]
    ])

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    ref = message.text.split(" ")[1] if len(message.text.split()) > 1 else None

    chat_member = await bot(GetChatMember(chat_id=CHANNEL_ID, user_id=user_id))
    if chat_member.status == "left":
        return await message.answer(f"Подпишитесь на канал {CHANNEL_ID} и попробуйте снова.")

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, balance, referrer) VALUES (?, ?, ?)",
                       (user_id, 100, int(ref) if ref and ref.isdigit() else None))
        if ref and ref.isdigit():
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (int(ref),))
        conn.commit()

    await message.answer(f"Добро пожаловать, {hbold(message.from_user.full_name)}!", reply_markup=main_keyboard())

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    cursor.execute("SELECT balance, referrals FROM users WHERE user_id = ?", (callback.from_user.id,))
    bal, refs = cursor.fetchone()
    await callback.message.edit_text(f"👤 Ваш профиль\n💰 Баланс: {bal}\n👥 Рефералы: {refs}", reply_markup=main_keyboard())

@dp.callback_query(F.data == "top")
async def top(callback: CallbackQuery):
    cursor.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 10")
    top_bal = cursor.fetchall()

    cursor.execute("SELECT user_id, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    top_refs = cursor.fetchall()

    text = "<b>🏆 Топ по балансу:</b>\n"
    for i, (uid, bal) in enumerate(top_bal, 1):
        text += f"{i}. <a href='tg://user?id={uid}'>{uid}</a> — {bal} монет\n"

    text += "\n<b>👥 Топ по рефералам:</b>\n"
    for i, (uid, refs) in enumerate(top_refs, 1):
        text += f"{i}. <a href='tg://user?id={uid}'>{uid}</a> — {refs} рефералов\n"

    await callback.message.edit_text(text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "shop")
async def shop(callback: CallbackQuery):
    cursor.execute("SELECT id, name, price, income FROM items")
    items = cursor.fetchall()

    if not items:
        return await callback.message.edit_text("🛍 Магазин пуст", reply_markup=main_keyboard())

    text = "<b>🛍 Магазин предметов:</b>\n"
    for item_id, name, price, income in items:
        text += f"{item_id}. {name} — {price} монет (доход: {income}/ч)\n"

    text += "\nНапиши номер предмета для покупки."
    await callback.message.edit_text(text)

@dp.message(F.text.regexp(r"^\d+$"))
async def buy_item(message: Message):
    user_id = message.from_user.id
    item_id = int(message.text)

    cursor.execute("SELECT name, price FROM items WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    if not item:
        return await message.answer("❌ Предмет не найден.")

    name, price = item
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    balance = cursor.fetchone()[0]

    if balance < price:
        return await message.answer("❌ Недостаточно монет.")

    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
    cursor.execute("INSERT INTO inventory (user_id, item_id, count) VALUES (?, ?, 1) ON CONFLICT(user_id, item_id) DO UPDATE SET count = count + 1", (user_id, item_id))
    conn.commit()

    await message.answer(f"✅ Вы купили {name}")

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("""
        SELECT items.name, inventory.count FROM inventory
        JOIN items ON inventory.item_id = items.id
        WHERE inventory.user_id = ?
    """, (user_id,))
    items = cursor.fetchall()

    if not items:
        return await callback.message.edit_text("🎒 Ваш инвентарь пуст.", reply_markup=main_keyboard())

    text = "🎒 Ваш инвентарь:\n"
    for name, count in items:
        text += f"{name} — {count} шт.\n"

    await callback.message.edit_text(text, reply_markup=main_keyboard())

@dp.callback_query(F.data == "work")
async def show_jobs(callback: CallbackQuery):
    cursor.execute("SELECT id, name, reward FROM jobs")
    jobs = cursor.fetchall()

    if not jobs:
        return await callback.message.edit_text("💼 Нет доступных работ.", reply_markup=main_keyboard())

    text = "<b>💼 Доступные работы:</b>\n"
    for job_id, name, reward in jobs:
        text += f"{job_id}. {name} — {reward} монет\n"

    text += "\nНапиши номер работы для выполнения."
    await callback.message.edit_text(text)

@dp.message(F.text.regexp(r"^\d+$"))
async def do_job(message: Message):
    job_id = int(message.text)
    user_id = message.from_user.id

    cursor.execute("SELECT name, reward FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    if not job:
        return await message.answer("❌ Работа не найдена.")

    name, reward = job
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
    conn.commit()

    await message.answer(f"✅ Вы выполнили {name} и получили {reward} монет.")

@dp.callback_query(F.data == "promo")
async def promo_start(callback: CallbackQuery):
    await callback.message.edit_text("🎁 Введите промокод:")

@dp.message()
async def promo_check(message: Message):
    code = message.text.strip()
    user_id = message.from_user.id

    cursor.execute("SELECT reward FROM promo WHERE code = ?", (code,))
    result = cursor.fetchone()
    if not result:
        return

    reward = result[0]
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
    cursor.execute("DELETE FROM promo WHERE code = ?", (code,))
    conn.commit()
    await message.answer(f"✅ Промокод активирован! Вы получили {reward} монет.")

# Фоновая задача — начисление пассивного дохода
async def passive_income():
    while True:
        cursor.execute("""
            SELECT user_id, SUM(items.income * inventory.count)
            FROM inventory
            JOIN items ON inventory.item_id = items.id
            GROUP BY user_id
        """)
        income_data = cursor.fetchall()

        for user_id, total_income in income_data:
            if total_income:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (total_income, user_id))

        conn.commit()
        await asyncio.sleep(3600)

async def main():
    asyncio.create_task(passive_income())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



