import os
import json
from datetime import datetime
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           ReplyKeyboardRemove, InlineKeyboardMarkup,
                           InlineKeyboardButton)
from aiogram.utils.markdown import escape_md
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio
import logging

# --- Налаштування логування ---
logging.basicConfig(level=logging.INFO)

# --- Ініціалізація Flask ---
app = Flask(__name__)

# --- Конфігурація бота та константи ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SHEET_NAME = os.getenv("SHEET_NAME", "KYC Заявки")

# --- Ініціалізація Aiogram ---
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot, storage=storage)

# --- Підключення до Google Sheets ---
sheet = None
try:
    creds_json_str = os.getenv("GOOGLE_CREDS_JSON")
    if not creds_json_str:
        logging.warning("⚠️  Змінна GOOGLE_CREDS_JSON не знайдена. Робота з Google Sheets буде неможлива.")
    else:
        creds_json = json.loads(creds_json_str)
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).sheet1
        logging.info("✅ Успішно підключено до Google Sheets.")
except Exception as e:
    logging.error(f"❌ Помилка підключення до Google Sheets: {e}")
    if ADMIN_ID:
        asyncio.run(bot.send_message(ADMIN_ID, f"Помилка підключення до Google Sheets: {e}", parse_mode=None))

# --- Клавіатури ---
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('ℹ️ Інфо'))
main_menu.add(KeyboardButton('📝 Заповнити заявку'))
main_menu.add(KeyboardButton('❓ FAQ'))

# --- Машина станів (FSM) для анкети ---
class ApplicationStates(StatesGroup):
    name = State()
    age = State()
    city = State()
    documents = State()
    experience = State()
    phone = State()

# --- Обробники команд та повідомлень ---

@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    text = """
Привіт! 👋 Це офіційний бот проєкту KYC Team — підробіток на проходженні верифікації (KYC) на криптобіржах 💼

🔒 Безпечно  
💸 Від 100 до 400 грн за заявку  
🕐 10–20 хвилин  
📱 Потрібно лише Паспорт/ID + селфі

⬇️ Обери, що тебе цікавить нижче на кнопках щоб дізнатися більше.
"""
    await message.answer(text, reply_markup=main_menu, parse_mode=None)

@dp.message_handler(text='ℹ️ Інфо', state='*')
async def send_info(message: types.Message):
    await message.answer("""
🔹 *Хто ми?* Ми допомагаємо людям заробити на проходженні верифікацій (KYC) для криптобірж.

🔹 *Як це працює?* 1. Ти заходиш в акаунт по нашим даним або ж по посиланню (інструкції даємо)  
2. Проходиш верифікацію  
3. Отримуєш оплату відразу після перевірки

🔹 *Законно?* Так. Це не шахрайство, не банки, не кредити.

🔹 *Скільки платимо?* 100–400 грн за заявку (заявок може бути багато). Виплата одразу після підтвердження.
""")

@dp.message_handler(text='❓ FAQ', state='*')
async def send_faq(message: types.Message):
    await message.answer("""
❓ *Часті питання:*
    
1. *Які документи потрібні?*
   - Паспорт або ID-карта, водійське, загран
   - Селфі з документом

2. *Як відбувається оплата?*
   - На карту або криптовалюту після успішної верифікації

3. *Скільки часу займає?*
   - Від 10 до 20 хвилин на одну заявку

4. *Чи це безпечно?*
   - Так, ми працюємо тільки з офіційними біржами
""")

@dp.message_handler(text='📝 Заповнити заявку', state='*')
async def start_application(message: types.Message):
    await message.answer("*1. Ваше Ім'я та нік в Telegram?*", reply_markup=ReplyKeyboardRemove())
    await ApplicationStates.name.set()

# --- Ланцюжок обробників для анкети ---

@dp.message_handler(state=ApplicationStates.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("*2. Скільки вам повних років?*")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.age)
async def process_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Будь ласка, введіть вік числом.")
        return
    async with state.proxy() as data:
        data['age'] = message.text
    await message.answer("*3. З якого ви міста?*")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.city)
async def process_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text
    await message.answer("*4. Які документи маєте (наприклад: Паспорт, ID-карта, водійське)?*")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.documents)
async def process_documents(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['documents'] = message.text
    await message.answer("*5. Чи проходили раніше верифікації (якщо так, то де саме)?*")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.experience)
async def process_experience(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = message.text
    await message.answer("*6. Ваш номер телефону для зв'язку?*")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
        user = message.from_user

        # --- ГОЛОВНЕ ВИПРАВЛЕННЯ: Формуємо повідомлення для адміна найнадійнішим способом ---
        # Поміщаємо всі дані від користувача в блок коду (```), де форматування не працює.
        user_data_block = (
            f"Ім'я:       {data['name']}\n"
            f"Вік:        {data['age']}\n"
            f"Місто:      {data['city']}\n"
            f"Документи:  {data['documents']}\n"
            f"Досвід:     {data['experience']}\n"
            f"Контакт:    {data['phone']}"
        )

        admin_message = (
            f"📨 *Нова заявка від @{escape_md(user.username or 'N/A')}*\n\n"
            f"```{user_data_block}```"
        )
        
        sheet_row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data['name'], data['age'], data['city'],
            data['documents'], data['experience'], data['phone'],
            str(user.id),
            f"@{user.username}" if user.username else "немає",
            f"{user.first_name or ''} {user.last_name or ''}".strip()
        ]

    try:
        if sheet:
            sheet.append_row(sheet_row)
            logging.info(f"Записано нову заявку в Google Sheets від {user.id}")

        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                admin_message,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("✍️ Написати користувачу", url=f"tg://user?id={user.id}")
                )
            )

        await message.answer(
                "✅ Дякуємо, вашу заявку отримано!\n"
                "🔗 Долучайтесь до нашої групи з завданнями:\n"
                "👉 https://t.me/+06666cc2_TwwMDZi\n"
                "❗ По будь яким питанням можете писати менеджеру в описі групи.",
            reply_markup=main_menu
        )

    except Exception as e:
        logging.error(f"❌ Помилка при фіналізації заявки від {user.id}: {e}")
        if ADMIN_ID:
            # Надсилаємо повідомлення про помилку без форматування, щоб уникнути нових помилок
            await bot.send_message(ADMIN_ID, f"❌ Помилка запису заявки від {user.id}:\n{e}", parse_mode=None)
        await message.answer("❌ Сталася невідома помилка. Спробуйте, будь ласка, пізніше.", reply_markup=main_menu, parse_mode=None)
    
    finally:
        await state.finish()

# --- Налаштування Webhook для Flask ---

@app.route('/webhook', methods=["POST"])
def webhook_handler():
    Bot.set_current(bot)
    Dispatcher.set_current(dp)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        update = types.Update(**request.json)
        loop.run_until_complete(dp.process_update(update))
    except Exception as e:
        logging.error(f"Помилка в обробнику вебхука: {e}", exc_info=True)
        
    return "ok", 200

@app.route('/')
def health_check():
    return "✅ Bot is alive and kicking!", 200

# Цей блок не виконується на Render, оскільки він використовує WSGI сервер (Gunicorn)
if __name__ == '__main__':
    pass
