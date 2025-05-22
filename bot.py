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
ADMIN_USERNAMES = ["@noaulish"]

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML, session=AiohttpSession())
dp = Dispatcher()

# Настройка логов
logging.basicConfig(level=logging.INFO)

# SQLite
conn = sqlite3.connect("bot.db")
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    referrer INTEGER,
    referrals INTEGER DEFAULT 0,
    vip INTEGER DEFAULT 0
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

# Инициализация предметов и работ
def initialize_items_and_jobs():
    cursor.execute("SELECT COUNT(*) FROM items")
    if cursor.fetchone()[0] == 0:
        for i in range(30):
            name = f"Предмет {i+1}"
            price = (i+1)*100
            income = (i+1)*10
            cursor.execute("INSERT INTO items (name, price, income) VALUES (?, ?, ?)", (name, price, income))
    cursor.execute("SELECT COUNT(*) FROM jobs")
    if cursor.fetchone()[0] == 0:
        job_list = [
            ("Курьер", 50),
            ("Продавец", 60),
            ("Официант", 70),
            ("Кассир", 80),
            ("Грузчик", 90),
            ("Повар", 100),
            ("Бармен", 110),
            ("Программист", 120),
            ("Дизайнер", 130),
            ("Инженер", 140),
            ("Водитель", 150),
            ("Таксист", 160),
            ("Адвокат", 170),
            ("Врач", 180),
            ("Пилот", 200)
        ]
        for name, reward in job_list:
            cursor.execute("INSERT INTO jobs (name, reward) VALUES (?, ?)", (name, reward))
    conn.commit()

initialize_items_and_jobs()

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

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],
        [InlineKeyboardButton(text="🛠 Памятка", callback_data="admin_help")]
    ])

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    ref = message.text.split(" ")[1] if len(message.text.split()) > 1 else None

    chat_member = await bot(GetChatMember(chat_id=CHANNEL_ID, user_id=user_id))
    if chat_member.status == "left":
        return await message.answer(f"Подпишитесь на канал {CHANNEL_ID} и попробуйте снова.")

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, balance, referrer) VALUES (?, ?, ?, ?)",
                       (user_id, username, 100, int(ref) if ref and ref.isdigit() else None))
        if ref and ref.isdigit():
            cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (int(ref),))
        conn.commit()

    await message.answer(f"Добро пожаловать, {hbold(message.from_user.full_name)}!", reply_markup=main_keyboard())

@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    cursor.execute("SELECT balance, referrals, vip FROM users WHERE user_id = ?", (callback.from_user.id,))
    bal, refs, vip = cursor.fetchone()
    vip_status = "✅" if vip else "❌"
    await callback.message.edit_text(f"👤 Ваш профиль\n💰 Баланс: {bal}\n👥 Рефералы: {refs}\n💎 VIP: {vip_status}", reply_markup=main_keyboard())

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
    job_id =
::contentReference[oaicite:31]{index=31}



