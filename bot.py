import asyncio
import logging
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"

bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

DB_NAME = "economy.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            inventory TEXT DEFAULT '',
            last_spin INTEGER DEFAULT 0
        )''')
        await db.commit()

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()
    await msg.answer("🎮 Добро пожаловать в экономическую игру! Используй /help для списка команд.")

@dp.message_handler(commands=["help"])
async def help(msg: types.Message):
    await msg.answer("""
Команды:
💰 /balance — баланс
🎁 /daily — ежедневная рулетка
🎲 /casino — казино
🪙 /coin — орёл и решка
🛒 /shop — магазин
🎒 /inventory — инвентарь
💎 /vip — купить VIP (200000 монет)
🛡 /mod — купить модерку (10000000 монет)
""")

@dp.message_handler(commands=["balance"])
async def balance(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as c:
            row = await c.fetchone()
            await msg.answer(f"💰 Баланс: {row[0]} монет")

@dp.message_handler(commands=["daily"])
async def daily(msg: types.Message):
    import time
    user_id = msg.from_user.id
    now = int(time.time())
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT last_spin FROM users WHERE user_id = ?", (user_id,)) as c:
            row = await c.fetchone()
            if now - row[0] < 86400:
                await msg.answer("⏳ Ты уже получал рулетку сегодня. Попробуй позже.")
                return
        reward = random.randint(100, 5000)
        await db.execute("UPDATE users SET balance = balance + ?, last_spin = ? WHERE user_id = ?", (reward, now, user_id))
        await db.commit()
        await msg.answer(f"🎁 Ты получил {reward} монет!")

@dp.message_handler(commands=["casino"])
async def casino(msg: types.Message):
    user_id = msg.from_user.id
    win = random.choice([True, False])
    amount = random.randint(100, 10000)
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as c:
            bal = (await c.fetchone())[0]
        if bal < amount:
            await msg.answer("❌ Недостаточно монет для игры в казино.")
            return
        if win:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await msg.answer(f"🎉 Ты выиграл {amount} монет!")
        else:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
            await msg.answer(f"😢 Ты проиграл {amount} монет.")
        await db.commit()

@dp.message_handler(commands=["coin"])
async def coin(msg: types.Message):
    user_id = msg.from_user.id
    choice = random.choice(["Орёл", "Решка"])
    reward = random.randint(500, 1500)
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (reward, user_id))
        await db.commit()
    await msg.answer(f"🪙 Выпал {choice}! Ты получил {reward} монет!")

items = [
    ("Кот в шляпе", 1000),
    ("Супер тапки", 2500),
    ("Пельмени", 500),
    ("Гармония", 3000),
    ("Стикербомб", 4000),
    ("Тостер", 1500),
    ("Кепка", 1800),
    ("Крутая футболка", 3000),
    ("Карандаш", 800),
    ("Ручка", 900),
]

@dp.message_handler(commands=["shop"])
async def shop(msg: types.Message):
    text = "🛒 Магазин:\n"
    for i, (name, price) in enumerate(items, 1):
        text += f"{i}. {name} — {price} монет\n"
    text += "\nКупить: /buy <номер>"
    await msg.answer(text)

@dp.message_handler(lambda m: m.text.startswith("/buy"))
async def buy(msg: types.Message):
    parts = msg.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await msg.answer("❌ Пример использования: /buy 1")
        return
    index = int(parts[1]) - 1
    if index < 0 or index >= len(items):
        await msg.answer("❌ Нет такого предмета.")
        return
    item_name, price = items[index]
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance, inventory FROM users WHERE user_id = ?", (user_id,))
        bal, inv = await cur.fetchone()
        if bal < price:
            await msg.answer("❌ Недостаточно монет.")
            return
        new_inv = inv + f"{item_name}," if inv else f"{item_name},"
        await db.execute("UPDATE users SET balance = balance - ?, inventory = ? WHERE user_id = ?", (price, new_inv, user_id))
        await db.commit()
        await msg.answer(f"✅ Покупка успешна: {item_name}")

@dp.message_handler(commands=["inventory"])
async def inventory(msg: types.Message):
    user_id = msg.from_user.id
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT inventory FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row or not row[0]:
            await msg.answer("🎒 У тебя пока ничего нет.")
        else:
            inv = row[0].split(",")[:-1]
            await msg.answer("🎒 Твой инвентарь:\n" + "\n".join(f"- {x}" for x in inv))

@dp.message_handler(commands=["vip"])
async def vip(msg: types.Message):
    user_id = msg.from_user.id
    cost = 200000
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = (await cur.fetchone())[0]
        if bal < cost:
            await msg.answer("❌ Недостаточно монет для покупки VIP.")
        else:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))
            await db.commit()
            await msg.answer("🎉 Поздравляем! Ты стал VIP!")

@dp.message_handler(commands=["mod"])
async def mod(msg: types.Message):
    user_id = msg.from_user.id
    cost = 10000000
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        bal = (await cur.fetchone())[0]
        if bal < cost:
            await msg.answer("❌ Недостаточно монет для покупки модера.")
        else:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (cost, user_id))
            await db.commit()
            await msg.answer("🛡 Теперь ты модератор!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.get_event_loop().run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)


