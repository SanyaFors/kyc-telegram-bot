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
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import asyncio

# Flask
app = Flask(__name__)

# Telegram bot
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Google Sheets
try:
    creds_json = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open(os.getenv("SHEET_NAME", "KYC Заявки")).sheet1
except Exception as e:
    print(f"\u26a0\ufe0f Google Sheets помилка: {e}")
    if ADMIN_ID:
        asyncio.get_event_loop().create_task(bot.send_message(ADMIN_ID, f"\u274c Помилка підключення до Google Sheets: {e}"))

# Меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('\u2139\ufe0f Інфо'))
main_menu.add(KeyboardButton('📝 Заповнити заявку'))
main_menu.add(KeyboardButton('❓ FAQ'))

# Стан машини
class ApplicationStates(StatesGroup):
    name = State()
    age = State()
    city = State()
    experience = State()
    phone = State()

# Команди
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    text = """
Привіт! 👋 Це офіційний бот проєкту KYC Team — підробіток на проходженні верифікації (KYC) на криптобіржах 💼

🔒 Безпечно  
💸 Від 100 до 400 грн за заявку  
🕐 10–20 хвилин  
📱 Потрібно лише Паспорт/ID + селфі

⬇️ Обери, що тебе цікавить нижче на кнопках щоб дізнатися більше.
"""
    await message.answer(text, reply_markup=main_menu)

@dp.message_handler(text='ℹ\ufe0f Інфо')
async def send_info(message: types.Message):
    await message.answer(
        """
🔹 Хто ми?  
Ми допомагаємо людям заробити на проходженні верифікацій (KYC) для криптобірж.

🔹 Як це працює?  
1. Ти заходиш в акаунт по нашим даним або ж по посиланню (інструкції даємо)  
2. Проходиш верифікацію  
3. Отримуєш оплату відразу після перевірки

🔹 Законно?  
Так. Це не шахрайство, не банки, не кредити.

🔹 Скільки платимо?  
100–400 грн за заявку (заявок може бути багато). Виплата одразу після підтвердження.
""",
        parse_mode="Markdown")

@dp.message_handler(text='❓ FAQ')
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
""", parse_mode="Markdown")

@dp.message_handler(text='📝 Заповнити заявку')
async def start_application(message: types.Message):
    await message.answer("✍️ Відповідай на питання по одному. Почнемо!\n\n1. Ваше Ім'я та нік в Telegram?", reply_markup=ReplyKeyboardRemove())
    await ApplicationStates.name.set()

@dp.message_handler(state=ApplicationStates.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("2. Скільки вам років?")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.age)
async def process_age(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['age'] = message.text
    await message.answer("3. З якого ви міста?")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.city)
async def process_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text
    await message.answer("4. Які документи маєте (паспорт, ID, водійське тощо)?")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.experience)
async def process_exp(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = message.text
    await message.answer("5. Чи проходили раніше верифікації (якщо так то де?)")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
        user = message.from_user
        try:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                data['name'], data['age'], data['city'],
                data['experience'], data['phone'],
                str(user.id),
                f"@{user.username}" if user.username else "немає",
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            ]
            sheet.append_row(row)

            await bot.send_message(
                ADMIN_ID,
                f"\ud83d\uddcb Нова заявка:\n\nІм'я: {data['name']}\nВік: {data['age']}\nМісто: {data['city']}\nДокументи: {data['experience']}\nКонтакт: {data['phone']}",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("Написати", url=f"tg://user?id={user.id}")
                ),
                parse_mode="Markdown"
            )

            await message.answer(
                "✅ Дякуємо, вашу заявку отримано!\n"
                "🔗 Долучайтесь до нашої групи з завданнями:\n"
                "👉 https://t.me/+06666cc2_TwwMDZi\n"
                "❗ По будь яким питанням можете писати менеджеру в описі групи.",
                reply_markup=main_menu
            )
        except Exception as e:
            print(f"❌ Помилка: {e}")
            if ADMIN_ID:
                await bot.send_message(ADMIN_ID, f"❌ Помилка запису: {e}")
            await message.answer("❌ Сталася помилка. Спробуйте пізніше.", reply_markup=main_menu)
    await state.finish()

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
async def webhook():
    update = types.Update(**request.json)
    await dp.process_update(update)
    return "ok", 200

# Health check
@app.route('/')
def health():
    return "✅ Bot is alive!", 200

# Встановлення webhook
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook встановлено: {WEBHOOK_URL}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(on_startup())
    app.run(host='0.0.0.0', port=10000)
