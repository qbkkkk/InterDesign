import asyncio
import os
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
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

# зберігаємо відповідність повідомлень
message_map = {}  # admin_msg_id -> user_id


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


# --- ОСНОВНА ЛОГІКА ---
@dp.message()
async def handler(message: types.Message):
    user_id = message.from_user.id

    # --- КЛІЄНТ ---
    if user_id != ADMIN_ID:

        # пересилаємо адміну
        sent = await bot.send_message(
            ADMIN_ID,
            f"👤 Клієнт:\n{message.text}"
        )

        # запамʼятовуємо
        message_map[sent.message_id] = user_id

        # AI відповідає
        if mode == "ai":
            response = model.generate_content(f"""
Ти — професійний менеджер з продажу студії Interdesign.
Відповідай коротко, продаюче, українською мовою.
Задавай уточнюючі питання і веди до консультації.

Клієнт: {message.text}
""")
            await message.answer(response.text)

    # --- АДМІН ---
    else:
        # якщо відповідаєш на повідомлення (Reply)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id

            if reply_id in message_map:
                client_id = message_map[reply_id]

                await bot.send_message(client_id, message.text)
            else:
                await message.answer("Не знайшов клієнта 😢")

        else:
            await message.answer("Відповідай через 'Reply' на повідомлення клієнта")


# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
