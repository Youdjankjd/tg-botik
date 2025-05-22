import asyncio
import random
import time
import aiosqlite
from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
CHANNEL_USERNAME = "economicbotlive"
ADMIN_IDS = [6505085514]
DB_NAME = "bot.db"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

main_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🎰 Казино"), KeyboardButton(text="🎁 Рулетка")],
    [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="💼 Работа"), KeyboardButton(text="🎒 Инвентарь")],
    [KeyboardButton(text="👑 ТОП"), KeyboardButton(text="👥 Рефералы")]
], resize_keyboard=True)

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ("left", "kicked"):
            raise TelegramBadRequest("Not subscribed")
    except:
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton(text="✅ Проверить подписку", callback_data="check_sub")]
        ])
        await message.answer("❗ Чтобы пользоваться ботом, подпишитесь на канал и нажмите «Проверить подписку».", reply_markup=markup)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, vip INTEGER DEFAULT 0, mod INTEGER DEFAULT 0, referrer INTEGER, referrals INTEGER DEFAULT 0, last_daily INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS items (user_id INTEGER, item_name TEXT, amount INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS promocodes (code TEXT PRIMARY KEY, reward INTEGER)")
        await db.commit()

        user = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        if not await user.fetchone():
            ref = message.text.split(" ")
            ref_id = int(ref[1]) if len(ref) > 1 and ref[1].isdigit() else None
            await db.execute("INSERT INTO users (user_id, referrer) VALUES (?, ?)", (user_id, ref_id))
            if ref_id:
                await db.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = ?", (ref_id,))
            await db.commit()
    await message.answer("🎉 Добро пожаловать в экономический бот!", reply_markup=main_kb)

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_subscription(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        if member.status in ("left", "kicked"):
            raise Exception()
        await bot.send_message(user_id, "✅ Подписка подтверждена! Введите /start")
    except:
        await bot.send_message(user_id, "❌ Вы не подписаны на канал!")


@dp.message(F.text == "💰 Баланс")
async def balance(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        balance = (await user.fetchone())[0]
    await message.answer(f"💰 Ваш баланс: <b>{balance} монет</b>")

@dp.message(F.text == "🎰 Казино")
async def casino(message: Message):
    user_id = message.from_user.id
    bet = 100
    async with aiosqlite.connect(DB_NAME) as db:
        user = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = await user.fetchone()
        if row is None or row[0] < bet:
            await message.answer("❌ Недостаточно средств.")
            return
        result = random.choice([True, False, False])
        if result:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (bet, user_id))
            await message.answer("🎉 Вы выиграли 100 монет!")
        else:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (bet, user_id))
            await message.answer("😢 Вы проиграли 100 монет.")
        await db.commit()

@dp.message(F.text == "🎁 Рулетка")
async def daily(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,))
        last = (await row.fetchone())[0]
        now = int(time.time())
        if now - last < 86400:
            remaining = 86400 - (now - last)
            await message.answer(f"⏳ Приходите через {remaining // 3600}ч {remaining % 3600 // 60}м.")
            return
        reward = random.randint(50, 200)
        await db.execute("UPDATE users SET balance = balance + ?, last_daily = ? WHERE user_id = ?", (reward, now, user_id))
        await db.commit()
    await message.answer(f"🎁 Вы получили {reward} монет!")

@dp.message(F.text.startswith("/promo"))
async def promo(message: Message):
    parts = message.text.split(" ")
    if len(parts) < 2:
        await message.answer("❗ Использование: /promo КОД")
        return
    code = parts[1]
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        result = await db.execute("SELECT reward FROM promocodes WHERE code = ?", (code,))
        data = await result.fetchone()
        if not data:
            await message.answer("❌ Промокод не найден.")
            return
        reward = data[0]
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
        await db.execute("DELETE FROM promocodes WHERE code = ?", (code,))
        await db.commit()
    await message.answer(f"✅ Промокод активирован! Вы получили {reward} монет.")

@dp.message(F.text.startswith("/addpromo"))
async def add_promo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    parts = message.text.split(" ")
    if len(parts) < 3:
        await message.answer("❗ Использование: /addpromo КОД СУММА")
        return
    code = parts[1]
    try:
        reward = int(parts[2])
    except ValueError:
        return await message.answer("❗ Сумма должна быть числом.")
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR REPLACE INTO promocodes (code, reward) VALUES (?, ?)", (code, reward))
        await db.commit()
    await message.answer(f"✅ Промокод {code} на {reward} монет создан.")


@dp.message(F.text == "👥 Рефералы")
async def referrals(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        row = await db.execute("SELECT referrals FROM users WHERE user_id = ?", (user_id,))
        count = (await row.fetchone())[0]
    await message.answer(f"👥 Вы пригласили {count} пользователей.")
🔗 Ваша ссылка: https://t.me/{(await bot.me()).username}?start={user_id}")

@dp.message(F.text == "👑 ТОП")
async def top(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        top_money = await db.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT 5")
        top_ref = await db.execute("SELECT user_id, referrals FROM users ORDER BY referrals DESC LIMIT 5")
        money = await top_money.fetchall()
        refs = await top_ref.fetchall()
    msg = "💸 ТОП 5 по балансу:
"
    for i, (uid, bal) in enumerate(money, 1):
        msg += f"{i}. <a href='tg://user?id={uid}'>Пользователь</a> — {bal} монет
"
    msg += "
👥 ТОП 5 по рефералам:
"
    for i, (uid, r) in enumerate(refs, 1):
        msg += f"{i}. <a href='tg://user?id={uid}'>Пользователь</a> — {r} рефералов
"
    await message.answer(msg)

@dp.message(F.text == "🛒 Магазин")
async def shop(message: Message):
    await message.answer("🛒 В магазине пока ничего нет.")

@dp.message(F.text == "💼 Работа")
async def work(message: Message):
    earnings = random.randint(20, 100)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (earnings, message.from_user.id))
        await db.commit()
    await message.answer(f"💼 Вы поработали и получили {earnings} монет.")

@dp.message(F.text == "🎒 Инвентарь")
async def inventory(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        items = await db.execute("SELECT item_name, amount FROM items WHERE user_id = ?", (user_id,))
        data = await items.fetchall()
    if not data:
        await message.answer("🎒 Ваш инвентарь пуст.")
    else:
        text = "🎒 Ваш инвентарь:
" + "
".join([f"{name} — {amount} шт." for name, amount in data])
        await message.answer(text)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())



