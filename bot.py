import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils import executor

TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"

bot = Bot(token=TOKEN)
dp = Dispatcher()

SHOP_ITEMS = {
    "Банан": 100,
    "Шляпа": 250,
    "Тостер": 500,
    "Игрушечный танк": 700,
    "Флешка": 1000,
    "Утка": 1500,
    "Кактус": 2000,
    "Ковер": 3000,
    "Лампа": 5000,
    "Кот в коробке": 7500,
    "Микроскоп": 9000
}

@dp.message(commands=["start"])
async def start_handler(message: types.Message):
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                last_spin INTEGER DEFAULT 0,
                inventory TEXT DEFAULT '',
                is_vip INTEGER DEFAULT 0,
                is_mod INTEGER DEFAULT 0
            )
        """)
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.from_user.id,))
        await db.commit()
    await message.answer("Привет! Добро пожаловать в игру! 💰\nИспользуй /balance, /daily, /casino, /coinflip, /shop, /inventory")

@dp.message(commands=["balance"])
async def balance_handler(message: types.Message):
    async with aiosqlite.connect("db.sqlite3") as db:
        cursor = await db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,))
        row = await cursor.fetchone()
        await message.answer(f"💰 Ваш баланс: {row[0]} монет")

@dp.message(commands=["daily"])
async def daily_handler(message: types.Message):
    async with aiosqlite.connect("db.sqlite3") as db:
        cursor = await db.execute("SELECT last_spin, balance FROM users WHERE user_id = ?", (message.from_user.id,))
        last_spin, balance = await cursor.fetchone()
        now = int(asyncio.get_event_loop().time())
        if now - last_spin >= 86400:
            amount = random.randint(500, 5000)
            await db.execute("UPDATE users SET balance = balance + ?, last_spin = ? WHERE user_id = ?", (amount, now, message.from_user.id))
            await db.commit()
            await message.answer(f"🎉 Вы получили {amount} монет из ежедневной рулетки!")
        else:
            remaining = 86400 - (now - last_spin)
            await message.answer(f"⏳ Приходите через {int(remaining // 3600)}ч {int((remaining % 3600) // 60)}м")

@dp.message(commands=["casino"])
async def casino_handler(message: types.Message):
    amount = random.randint(-1000, 2000)
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, message.from_user.id))
        await db.commit()
    if amount >= 0:
        await message.answer(f"🎰 Вы выиграли {amount} монет!")
    else:
        await message.answer(f"💸 Вы проиграли {-amount} монет.")

@dp.message(commands=["coinflip"])
async def coinflip_handler(message: types.Message):
    outcome = random.choice(["Орел", "Решка"])
    win = random.choice([True, False])
    result = 1000 if win else -1000
    async with aiosqlite.connect("db.sqlite3") as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (result, message.from_user.id))
        await db.commit()
    if win:
        await message.answer(f"🪙 Выпал {outcome}. Вы выиграли 1000 монет!")
    else:
        await message.answer(f"🪙 Выпал {outcome}. Вы проиграли 1000 монет.")

@dp.message(commands=["shop"])
async def shop_handler(message: types.Message):
    text = "🛍 Магазин товаров:\n"
    for name, price in SHOP_ITEMS.items():
        text += f"{name} - {price} монет\n"
    text += "\nНапишите /buy <название> чтобы купить."
    await message.answer(text)

@dp.message(commands=["buy"])
async def buy_handler(message: types.Message):
    args = message.text.split(" ", 1)
    if len(args) < 2:
        return await message.answer("Введите название предмета. Пример: /buy Банан")
    item = args[1].strip()
    if item not in SHOP_ITEMS:
        return await message.answer("Такого предмета нет в магазине.")

    price = SHOP_ITEMS[item]
    async with aiosqlite.connect("db.sqlite3") as db:
        cursor = await db.execute("SELECT balance, inventory FROM users WHERE user_id = ?", (message.from_user.id,))
        balance, inventory = await cursor.fetchone()
        if balance < price:
            return await message.answer("Недостаточно монет.")
        new_inventory = inventory + f",{item}" if inventory else item
        await db.execute("UPDATE users SET balance = ?, inventory = ? WHERE user_id = ?", (balance - price, new_inventory, message.from_user.id))
        await db.commit()
    await message.answer(f"✅ Вы купили: {item}")

@dp.message(commands=["inventory"])
async def inventory_handler(message: types.Message):
    async with aiosqlite.connect("db.sqlite3") as db:
        cursor = await db.execute("SELECT inventory FROM users WHERE user_id = ?", (message.from_user.id,))
        inventory = (await cursor.fetchone())[0]
        if not inventory:
            await message.answer("🎒 Ваш инвентарь пуст.")
        else:
            items = inventory.split(",")
            await message.answer("🎒 Ваш инвентарь:\n" + "\n".join(items))

@dp.message(commands=["vip"])
async def vip_handler(message: types.Message):
    async with aiosqlite.connect("db.sqlite3") as db:
        cursor = await db.execute("SELECT balance, is_vip FROM users WHERE user_id = ?", (message.from_user.id,))
        balance, is_vip = await cursor.fetchone()
        if is_vip:
            return await message.answer("У вас уже есть VIP статус.")
        if balance < 200000:
            return await message.answer("Недостаточно монет для покупки VIP (нужно 200000).")
        await db.execute("UPDATE users SET balance = balance - 200000, is_vip = 1 WHERE user_id = ?", (message.from_user.id,))
        await db.commit()
    await message.answer("✨ Вы стали VIP игроком!")

@dp.message(commands=["mod"])
async def mod_handler(message: types.Message):
    async with aiosqlite.connect("db.sqlite3") as db:
        cursor = await db.execute("SELECT balance, is_mod FROM users WHERE user_id = ?", (message.from_user.id,))
        balance, is_mod = await cursor.fetchone()
        if is_mod:
            return await message.answer("Вы уже модератор.")
        if balance < 10000000:
            return await message.answer("Недостаточно монет для модерки (нужно 10000000).")
        await db.execute("UPDATE users SET balance = balance - 10000000, is_mod = 1 WHERE user_id = ?", (message.from_user.id,))
        await db.commit()
    await message.answer("🛡 Теперь вы модератор!")

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)

