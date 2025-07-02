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
        
        try:
            # Запис у Google Таблицю
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
                "👉 https://t.me/+06666cc2_TwwMDZi\n"
                "❗ По будь яким питанням можете писати менеджеру в описі групи.",
                parse_mode="Markdown",
                reply_markup=main_menu
            )
            
        except Exception as e:
            print(f"🚨 Помилка: {e}")
            if ADMIN_ID:
                await bot.send_message(ADMIN_ID, f"Помилка запису заявки: {e}")
            await message.answer(
                "❌ Виникла помилка при обробці заявки. Спробуйте пізніше або зв'яжіться з адміністратором.",
                reply_markup=main_menu
            )
    
    await state.finish()

if name == '__main__':
    # Запускаємо Flask у окремому потоці
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=10000, debug=False, use_reloader=False)
    ).start()
    
    # Запускаємо бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
