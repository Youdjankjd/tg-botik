import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
import random

API_TOKEN = "7558760680:AAHhhuACxlLgfkOwskeA5B9dzZ4GZp2uk8c"
CHANNEL_USERNAME = "@economicbotlive"
ADMINS = ["@noaulish"]

bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

# Временное хранилище пользователей, монет и т.д.
users_data = {}

# Данные магазина и работ
shop_items = [{"name": f"Предмет {i+1}", "price": (i+1)*100, "income": (i+1)*10} for i in range(30)]
jobs = [{"name": f"Работа {i+1}", "salary": (i+1)*50} for i in range(15)]

# Функции

def get_user_data(user_id):
    if user_id not in users_data:
        users_data[user_id] = {
            "coins": 100,
            "inventory": [],
            "job": None,
            "referrals": 0,
            "vip": False
        }
    return users_data[user_id]

async def check_subscription(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "creator", "administrator")
    except:
        return False

def is_admin(username):
    return username in ADMINS

# Команды

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if not await check_subscription(user_id):
        markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Подписаться", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")
        ]])
        await message.answer("❗ Для использования бота подпишитесь на канал.", reply_markup=markup)
        return

    args = message.text.split()
    if len(args) > 1:
        ref_id = int(args[1])
        if ref_id != user_id and ref_id in users_data:
            users_data[ref_id]["coins"] += 50
            users_data[ref_id]["referrals"] += 1

    await message.answer("👋 Добро пожаловать в экономический бот!", reply_markup=main_menu())

def main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="💼 Работа", callback_data="work")
    builder.button(text="🛒 Магазин", callback_data="shop")
    builder.button(text="🎒 Инвентарь", callback_data="inventory")
    builder.button(text="📊 Топ", callback_data="top")
    builder.button(text="🎰 Казино", callback_data="casino")
    builder.button(text="🎁 Промокод", callback_data="promo")
    return builder.as_markup()

@dp.callback_query(F.data == "work")
async def choose_work(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for i, job in enumerate(jobs[:15]):
        builder.button(text=f"{job['name']} — 💰{job['salary']}", callback_data=f"job_{i}")
    await callback.message.edit_text("💼 Выберите работу:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("job_"))
async def set_job(callback: types.CallbackQuery):
    index = int(callback.data.split("_")[1])
    user_data = get_user_data(callback.from_user.id)
    user_data["job"] = jobs[index]
    await callback.message.edit_text(f"✅ Вы устроились на работу: {jobs[index]['name']}")

@dp.callback_query(F.data == "shop")
async def show_shop(callback: types.CallbackQuery):
    text = "🛒 <b>Магазин предметов</b>"
    for i, item in enumerate(shop_items[:30]):
        name = "Пользователь"
text += f"Привет, {name}! Добро пожаловать."
{i+1}. {item['name']} — 💰{item['price']} | 📈 +{item['income']}/ч"
    await callback.message.edit_text(text)

@dp.callback_query(F.data == "inventory")
async def show_inventory(callback: types.CallbackQuery):
    user_data = get_user_data(callback.from_user.id)
    inventory = user_data["inventory"]
    if not inventory:
        await callback.message.edit_text("🎒 Ваш инвентарь пуст.")
        return
    text = "🎒 <b>Ваш инвентарь:</b>"
    for item in inventory:
        text += f"- {item['name']} (+{item['income']}/ч)"
    await callback.message.edit_text(text)

@dp.callback_query(F.data == "casino")
async def casino(callback: types.CallbackQuery):
    user_data = get_user_data(callback.from_user.id)
    win = random.randint(0, 100)
    if win < 40:
        amount = random.randint(10, 50)
        user_data["coins"] += amount
        await callback.message.edit_text(f"🎰 Вы выиграли {amount} монет!")
    else:
        amount = random.randint(10, 30)
        user_data["coins"] -= amount
        await callback.message.edit_text(f"🎰 Вы проиграли {amount} монет.")

@dp.callback_query(F.data == "promo")
async def promo(callback: types.CallbackQuery):
    await callback.message.edit_text("🎁 Промокоды доступны только от администратора.")

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.username):
        await message.answer("⛔ Нет доступа.")
        return
    await message.answer("🛠 Админ-панель:
/admin_stats
/admin_broadcast <текст>")

@dp.message(Command("admin_stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.username):
        return
    await message.answer(f"👥 Всего пользователей: {len(users_data)}")

@dp.message(Command("admin_broadcast"))
async def broadcast(message: Message):
    if not is_admin(message.from_user.username):
        return
    text = message.text[len("/admin_broadcast "):]
    for user_id in users_data:
        try:
            await bot.send_message(user_id, f"📢 Рассылка от админа:

{text}")
        except:
            continue
    await message.answer("✅ Рассылка завершена.")

async def income_loop():
    while True:
        await asyncio.sleep(3600)
        for user_id, data in users_data.items():
            for item in data["inventory"]:
                data["coins"] += item["income"]

async def main():
    asyncio.create_task(income_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())



