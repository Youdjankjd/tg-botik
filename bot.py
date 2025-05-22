import asyncio
import random
import time
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
import aiosqlite

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
CHANNEL_USERNAME = "@economicbotlive"
ADMIN_IDS = [6505085514]
DB_NAME = "bot.db"

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Клавиатура
main_kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton("💰 Баланс"), KeyboardButton("🎰 Казино"), KeyboardButton("🎁 Рулетка")],
    [KeyboardButton("🛒 Магазин"), KeyboardButton("💼 Работа"), KeyboardButton("📦 Инвентарь")],
    [KeyboardButton("👑 ТОП"), KeyboardButton("👥 Рефералы")]
])

subscribe_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🔗 Подписаться", url="https://t.me/economicbotlive")],
    [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
])

# Инициализация БД
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            vip INTEGER DEFAULT 0,
            mod INTEGER DEFAULT 0,
            referrer INTEGER,
            referrals INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS items (
            user_id INTEGER,
            item_name TEXT,
            amount INTEGER
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            reward INTEGER
        )""")
        await db.commit()

# Проверка подписки
async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Старт
@dp.message(F.text == "/start")
async def start_handler(msg: Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = await result.fetchone()
        if not user:
            args = msg.text.split()
            referrer = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
            await db.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, referrer))
            if referrer:
                await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (referrer,))
            await db.commit()

    if not await check_subscription(user_id):
        await msg.answer("👋 Привет! Чтобы играть, подпишись на наш канал:", reply_markup=subscribe_kb)
        return

    await msg.answer("Добро пожаловать в экономическую игру!", reply_markup=main_kb)

# Проверка подписки (по кнопке)
@dp.callback_query(F.data == "check_sub")
async def verify_subscription(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.edit_text("✅ Подписка подтверждена!")
        await callback.message.answer("Добро пожаловать!", reply_markup=main_kb)
    else:
        await callback.answer("❌ Вы не подписаны!", show_alert=True)

# Баланс
@dp.message(F.text == "💰 Баланс")
async def balance_handler(msg: Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        res = await db.execute("SELECT balance, vip, mod FROM users WHERE user_id = ?", (user_id,))
        user = await res.fetchone()
        if user:
            balance, vip, mod = user
            status = "Обычный"
            if vip:
                status = "VIP"
            if mod:
                status = "Модератор"
            await msg.answer(f"💰 Баланс: {balance} монет\n🏷 Статус: {status}")
        else:
            await msg.answer("❌ Вы не зарегистрированы. Напишите /start")

# Рулетка
@dp.message(F.text == "🎁 Рулетка")
async def roulette_handler(msg: Message):
    user_id = msg.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        res = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        last = (await res.fetchone())[0]
        if now - last < 86400:
            remain = 86400 - (now - last)
            hours = remain // 3600
            minutes = (remain % 3600) // 60
            await msg.answer(f"⏳ Уже крутили рулетку. Ждите {hours} ч. {minutes} мин.")
            return
        amount = random.choices([0, 500, 1000, 2500, 5000], weights=[50, 25, 15, 8, 2])[0]
        await db.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (amount, now, user_id))
        await db.commit()
        await msg.answer(f"🎉 Вы получили {amount} монет!")

# Казино
@dp.message(F.text == "🎰 Казино")
async def casino_handler(msg: Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        res = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = (await res.fetchone())[0]
        if balance >= 100:
            win = random.random() < 0.25
            delta = 1000 if win else -100
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (delta, user_id))
            await db.commit()
            text = "🎉 Вы выиграли 1000 монет!" if win else "😢 Вы проиграли 100 монет."
            await msg.answer(text)
        else:
            await msg.answer("❌ Не хватает монет (нужно 100+)")

# Промокоды
@dp.message(F.text.startswith("ПРОМО"))
async def promo_handler(msg: Message):
    code = msg.text.split("ПРОМО")[1].strip()
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        res = await db.execute("SELECT reward FROM promo_codes WHERE code = ?", (code,))
        promo = await res.fetchone()
        if promo:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (promo[0], user_id))
            await db.execute("DELETE FROM promo_codes WHERE code = ?", (code,))
            await db.commit()
            await msg.answer(f"🎁 Вы активировали промокод и получили {promo[0]} монет!")
        else:
            await msg.answer("❌ Неверный или использованный промокод.")

# Команда для добавления промокода
@dp.message(F.text.startswith("/addpromo"))
async def add_promo(msg: Message):
    if msg.from_user.id not in ADMIN_IDS:
        return await msg.answer("❌ У вас нет прав.")
    try:
        _, code, reward = msg.text.split()
        reward = int(reward)
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("INSERT INTO promo_codes (code, reward) VALUES (?, ?)", (code, reward))
            await db.commit()
            await msg.answer("✅ Промокод добавлен.")
    except:
        await msg.answer("Пример: /addpromo КОД 500")

# Запуск
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



