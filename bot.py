import asyncio
import time
import random
import aiosqlite
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
)
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
ADMIN_IDS = [6505085514]
CHANNEL_ID = "@economicbotlive"  # Используем username вместо числового ID

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"[Проверка подписки] Ошибка: {e}")
        return False
bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

DB_NAME = "bot.db"

main_kb = ReplyKeyboardMarkup(
    resize_keyboard=True, keyboard=[
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎰 Казино")],
        [KeyboardButton(text="🎁 Рулетка"), KeyboardButton(text="🛒 Магазин")],
        [KeyboardButton(text="🧰 Работа"), KeyboardButton(text="🎒 Инвентарь")],
        [KeyboardButton(text="👑 ТОП"), KeyboardButton(text="👥 Рефералы")]
    ]
)

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            referrer INTEGER,
            referrals INTEGER DEFAULT 0,
            last_daily INTEGER DEFAULT 0,
            vip INTEGER DEFAULT 0,
            admin INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS items (
            user_id INTEGER,
            item_name TEXT,
            amount INTEGER
        );
        CREATE TABLE IF NOT EXISTS promocodes (
            code TEXT PRIMARY KEY,
            reward INTEGER,
            used_by TEXT
        );
        """)
        await db.commit()

async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

@router.message(F.text == "/start")
async def start_cmd(message: Message):
    if not await is_subscribed(message.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Подписаться", url="https://t.me/economicbotlive")],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
        ])
        await message.answer("👋 Привет! Для использования бота подпишись на канал:", reply_markup=kb)
        return

    user_id = message.from_user.id
    ref = message.text.split(" ")[1] if len(message.text.split()) > 1 else None
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute_fetchone("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not user:
            ref_id = int(ref) if ref and ref.isdigit() and int(ref) != user_id else None
            await db.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, ref_id))
            if ref_id:
                await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
            await db.commit()
    await message.answer("🎉 Добро пожаловать в экономическую игру!", reply_markup=main_kb)

@router.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    if await is_subscribed(callback.from_user.id):
        await callback.message.delete()
        await start_cmd(callback.message)
    else:
        await callback.answer("❌ Вы не подписались!", show_alert=True)

@router.message(F.text == "💰 Баланс")
async def balance_cmd(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute_fetchone("SELECT balance, vip, admin FROM users WHERE user_id = ?", (user_id,))
        if row:
            balance, vip, admin = row
            status = "Обычный"
            if vip: status = "VIP"
            if admin: status = "Админ"
            await message.answer(f"💰 Баланс: {balance} монет\nСтатус: {status}")

@router.message(F.text == "🎰 Казино")
async def casino_cmd(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute_fetchone("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        if row and row[0] >= 100:
            win = random.random() < 0.25
            amount = 1000 if win else -100
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()
            await message.answer("🎉 Вы выиграли 1000 монет!" if win else "💸 Вы проиграли 100 монет.")
        else:
            await message.answer("❌ У вас меньше 100 монет!")

@router.message(F.text == "🎁 Рулетка")
async def roulette_cmd(message: Message):
    user_id = message.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute_fetchone("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        if row:
            last = row[0]
            if now - last < 86400:
                remaining = 86400 - (now - last)
                h, m = remaining // 3600, (remaining % 3600) // 60
                await message.answer(f"🕒 До следующей рулетки: {h} ч {m} мин.")
                return
            reward = random.choices([0, 500, 1000, 2500, 5000], weights=[50, 25, 15, 8, 2])[0]
            await db.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (reward, now, user_id))
            await db.commit()
            await message.answer(f"🎁 Вы получили {reward} монет!")

@router.message(F.text == "👑 ТОП")
async def top_cmd(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        rows = await db.execute_fetchall("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
        text = "🏆 Топ-5 игроков по балансу:\n\n"
        for i, (uid, bal) in enumerate(rows, 1):
            text += f"{i}. <a href='tg://user?id={uid}'>Игрок</a> — {bal} монет\n"
        await message.answer(text)

@router.message(F.text == "👥 Рефералы")
async def refs_cmd(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute_fetchone("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
        if row:
            count = row[0]
            await message.answer(f"👥 Вы пригласили {count} пользователей.\nВаша ссылка:\nhttps://t.me/economicbotlive?start={user_id}")

@router.message(F.text.startswith("/promo"))
async def promo_cmd(message: Message):
    code = message.text.split(" ")[1] if len(message.text.split()) > 1 else ""
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        promo = await db.execute_fetchone("SELECT reward, used_by FROM promocodes WHERE code = ?", (code,))
        if promo:
            reward, used_by = promo
            if used_by and str(user_id) in used_by.split(","):
                await message.answer("❗️Вы уже использовали этот промокод.")
            else:
                await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
                used = used_by + f",{user_id}" if used_by else str(user_id)
                await db.execute("UPDATE promocodes SET used_by = ? WHERE code = ?", (used, code))
                await db.commit()
                await message.answer(f"🎉 Вы получили {reward} монет по промокоду!")
        else:
            await message.answer("❌ Неверный промокод.")

@router.message(F.text.startswith("/createpromo"))
async def create_promo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("❌ Только для админов.")
    parts = message.text.split()
    if len(parts) < 3:
        return await message.answer("Пример: /createpromo NEWYEAR2025 1000")
    code, reward = parts[1], int(parts[2])
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO promocodes (code, reward) VALUES (?, ?)", (code, reward))
        await db.commit()
    await message.answer(f"✅ Промокод <b>{code}</b> на {reward} монет создан.")

async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



