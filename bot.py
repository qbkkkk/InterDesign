import os
import asyncio
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# --- ЗАВАНТАЖЕННЯ ENV ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = os.getenv("HF_MODEL", "gpt2")  # Можна обрати іншу модель

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

mode = "ai"  # ai / human
clients = {}  # client_id -> {"last_msg": str, "name": str}

HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}
API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL}"

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
async def ai_mode(message: types.Message):
    global mode
    if message.from_user.id == ADMIN_ID:
        mode = "ai"
        await message.answer("Режим: ШІ відповідає")

# --- ФУНКЦІЯ ДЛЯ HUGGING FACE ---
def query_hf(prompt: str):
    payload = {"inputs": prompt, "options": {"wait_for_model": True}}
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Hugging Face нові моделі можуть повертати list з 'generated_text'
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"]
        elif isinstance(data, dict) and "error" in data:
            return None
        return str(data)
    except Exception as e:
        return None

# --- ГОЛОВНИЙ ХЕНДЛЕР ---
@dp.message()
async def main_handler(message: types.Message):
    user_id = message.from_user.id

    if user_id == ADMIN_ID:
        # --- АДМІН ПИШЕ ---
        if "reply_to" in clients:
            client_id = clients["reply_to"]
            await bot.send_message(client_id, message.text)
            await message.answer(f"Відправлено клієнту {clients[client_id]['name']} ✅")
            del clients["reply_to"]
        else:
            await message.answer("Натисни кнопку 'Відповісти' на клієнта перед відправкою")
        return

    # --- КЛІЄНТ ПИШЕ ---
    clients[user_id] = {"last_msg": message.text, "name": message.from_user.full_name}

    # Кнопка для адміна відповісти
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
        # Твій промт Interdesign
        prompt = f"""Ти — професійний менеджер з продажу студії дизайну інтер’єру Interdesign (https://interdesign.com.ua/).

Твоя задача — не просто відповідати, а ПРОДАВАТИ послуги та переводити клієнта в дію (заявка / дзвінок / консультація).

Стиль спілкування:
- ввічливий, впевнений, без води
- простими словами, без складних термінів
- як жива людина, не як бот
- короткі відповіді (2–5 речень)
- українською мовою

Що ти продаєш:
- дизайн інтер’єру квартир, будинків, комерційних приміщень
- повний супровід проєкту
- планування, візуалізація, підбір матеріалів
- сучасний, функціональний дизайн

Твоя поведінка:
1. Завжди уточнюй:
   - тип об’єкта (квартира / будинок / комерція)
   - площу або хоча б приблизно
   - місто
2. Виявляй потребу:
   - що саме хоче клієнт
   - чи вже є ремонт / новобудова
3. Формуй цінність:
   - пояснюй вигоду дизайну (економія часу, уникнення помилок, стильний результат)
4. Закривай на дію:
   - запропонуй безкоштовну консультацію
   - або зв’язок з менеджером
5. Якщо питають ціну:
   - не давай суху цифру одразу
   - скажи, що залежить від площі і задачі
   - запропонуй прорахунок

Обмеження:
- не вигадуй того, чого немає на сайті
- не давай неправдиву інформацію
- якщо не впевнений — скажи, що уточниш

Формат відповіді:
- коротко
- по суті
- з питанням в кінці (щоб вести діалог)

Питання клієнта: {message.text}
"""

        reply_text = query_hf(prompt)
        if reply_text:
            await bot.send_message(user_id, reply_text)
        else:
            await bot.send_message(user_id, "Менеджер зараз зв'яжеться з вами 📞")
            await bot.send_message(ADMIN_ID, f"❌ Hugging Face не відповів для {message.from_user.full_name} ({user_id})")

# --- CALLBACK для кнопок ---
@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    data = callback.data
    if data.startswith("reply_") and callback.from_user.id == ADMIN_ID:
        client_id = int(data.split("_")[1])
        if client_id in clients:
            await callback.message.answer(f"Відповідь на клієнта {clients[client_id]['name']} (тут напишіть текст, він відправиться клієнту)")
            clients["reply_to"] = client_id
        else:
            await callback.message.answer("Клієнт не знайдений 😢")

# --- ЗАПУСК ---
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
