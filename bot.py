import asyncio
import os
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

mode = "ai"  # ai / human

# CRM-подібне зберігання клієнтів
clients = {}  # client_id -> {"last_msg": str, "name": str}

# --- СТАРТ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Вітаємо! Напишіть ваше питання 👇")

# --- РЕЖИМИ ---
@dp.message(Command("human"))
async def human(message: types.Message):
    global mode
    if message.from_user.id == ADMIN_ID:
        mode = "human"
        await message.answer("Режим: ти відповідаєш")

@dp.message(Command("ai"))
async def ai(message: types.Message):
    global mode
    if message.from_user.id == ADMIN_ID:
        mode = "ai"
        await message.answer("Режим: ШІ відповідає")

# --- КЛІЄНТ ПИШЕ ---
@dp.message()
async def handler(message: types.Message):
    user_id = message.from_user.id

    # --- КЛІЄНТ ---
    if user_id != ADMIN_ID:
        clients[user_id] = {"last_msg": message.text, "name": message.from_user.full_name}

        # кнопка для адміна: відповісти
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Відповісти", callback_data=f"reply_{user_id}")]
        ])

        await bot.send_message(
            ADMIN_ID,
            f"👤 Клієнт: {message.from_user.full_name}\n\n{message.text}",
            reply_markup=keyboard
        )

        # ШІ відповідає якщо режим ai
        if mode == "ai":
            try:
                response = model.generate_content(f"""
Ти — професійний менеджер з продажу студії Interdesign (https://interdesign.com.ua/).
Відповідай коротко, продаюче, українською мовою.
Задавай уточнюючі питання і веди до консультації.

Клієнт: {message.text}
""")
                await bot.send_message(user_id, response.text)
            except Exception as e:
                await bot.send_message(user_id, "Помилка відповіді 😢")
                print("GEMINI ERROR:", e)

# --- CALLBACK для кнопок ---
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data
    if data.startswith("reply_") and callback.from_user.id == ADMIN_ID:
        client_id = int(data.split("_")[1])
        if client_id in clients:
            await callback.message.answer(f"Відповідь на клієнта {clients[client_id]['name']} (нажми тут і пиши текст)")
            # зберігаємо id клієнта, якого будемо відповісти
            clients["reply_to"] = client_id
        else:
            await callback.message.answer("Клієнт не знайдений 😢")

# --- АДМІН ПИШЕ ---
@dp.message()
async def admin_message(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        if "reply_to" in clients:
            client_id = clients["reply_to"]
            await bot.send_message(client_id, message.text)
            await message.answer(f"Відправлено клієнту {clients[client_id]['name']} ✅")
            del clients["reply_to"]
        else:
            await message.answer("Натисни кнопку 'Відповісти' на клієнта перед відправкою")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
