import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                          ReplyKeyboardRemove, InlineKeyboardMarkup, 
                          InlineKeyboardButton)
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Ініціалізація бота через змінні середовища
storage = MemoryStorage()
bot = Bot(token=os.getenv("BOT_TOKEN"))  # Токен з Render
ADMIN_ID = os.getenv("ADMIN_ID")         # Ваш Telegram ID
dp = Dispatcher(bot, storage=storage)

# Конфігурація Google Sheets
try:
    # Отримання облікових даних з змінної середовища
    creds_json = json.loads(os.getenv("GOOGLE_CREDS_JSON"))
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open(os.getenv("SHEET_NAME", "KYC Заявки")).sheet1
except Exception as e:
    print(f"🚨 Помилка підключення до Google Sheets: {e}")
    # Відправка повідомлення адміну про помилку
    if ADMIN_ID:
        error_msg = "🔴 Помилка підключення до Google Sheets. Терміново перевірте логи!"
        async def notify_admin(error_msg: str):
    try:
        await bot.send_message(ADMIN_ID, error_msg)
    except Exception as e:
        print(f"Не вдалося відправити помилку адміну: {e}")

# Головне меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton('ℹ️ Інфо'))
main_menu.add(KeyboardButton('📝 Заповнити заявку'))
main_menu.add(KeyboardButton('❓ FAQ'))

# Обробник команди /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    welcome_text = """
    Привіт! 👋 Це офіційний бот проєкту KYC Team — підробіток на проходженні верифікації (KYC) на криптобіржах 💼

🔒 Безпечно  
💸 Від 100 до 400 грн за заявку  
🕐 10–20 хвилин  
📱 Потрібно лише Паспорт/ID + селфі

⬇️ Обери, що тебе цікавить нижче на кнопках щоб дізнатися більше.
    """
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=main_menu)

# Стани для заявки
class ApplicationStates(StatesGroup):
    name = State()
    age = State()
    city = State()
    experience = State()
    phone = State()

# Обробник кнопки "Заповнити заявку"
@dp.message_handler(text='📝 Заповнити заявку')
async def start_application(message: types.Message):
    await message.answer("✍️ Відповідай на питання по одному. Почнемо!\n\n1. Ваше Ім'я та нік в Telegram?", reply_markup=ReplyKeyboardRemove())
    await ApplicationStates.name.set()

# Обробник відповідей на заявку
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
async def process_experience(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = message.text
    await message.answer("5. Чи проходили раніше верифікації (якщо так то де?)")
    await ApplicationStates.next()

@dp.message_handler(state=ApplicationStates.phone)
async def process_phone(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['phone'] = message.text
        user = message.from_user
        
        # Запис у Google Таблицю
        try:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                data['name'],
                data['age'],
                data['city'],
                data['experience'],
                data['phone'],
                str(user.id),
                f"@{user.username}" if user.username else "немає",
                f"{user.first_name or ''} {user.last_name or ''}".strip()
            ]
            sheet.append_row(row)
        except Exception as e:
            print(f"🚨 Помилка запису в Google Sheets: {e}")
            if ADMIN_ID:
                await bot.send_message(ADMIN_ID, f"Помилка запису заявки: {e}")
        
        # Повідомлення адміну
        admin_msg = f"""
📄 *Нова заявка!*
🕒 {datetime.now().strftime("%d.%m.%Y %H:%M")}

👤 *Ім'я:* {data['name']}
🔢 *Вік:* {data['age']}
🏙️ *Місто:* {data['city']}
📄 *Документи:* {data['experience']}
📱 *Контакт:* {data['phone']}

👤 *Користувач:*
ID: {user.id}
Username: {'@' + user.username if user.username else 'немає'}
Ім'я: {user.first_name or ''} {user.last_name or ''}
        """
        
        await bot.send_message(
            ADMIN_ID,
            admin_msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton(
                    "Написати користувачу",
                    url=f"tg://user?id={user.id}"
                )
            )
        )
        
        # Відповідь користувачу
        await message.answer(
            "✅ Дякуємо, вашу заявку отримано!\n"
            "🔗 Долучайтесь до нашої групи з завданнями:\n"
            "👉 https://t.me/destorkycteam"
            "❗ По будь яким питанням можете писати менеджеру в описі групи.",
            parse_mode="Markdown",
            reply_markup=main_menu
        )
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
