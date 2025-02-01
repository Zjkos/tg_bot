import telebot
from telebot import types
import sqlite3
import pandas as pd
import openpyxl


bot = telebot.TeleBot('TG_token')

# Глобальная переменная для временного хранения данных пользователя
user_data = {}

# Подключение к базе данных
conn = sqlite3.connect('construction_services.db')
with conn:
    # Создание таблица данных объекта (площадь/длина и прочее)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            floor_length REAL NOT NULL,
            floor_width REAL NOT NULL,
            room_height REAL NOT NULL,
            window_area REAL NOT NULL
        )
    ''')

    # Создание таблицы с услугами
    conn.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            price_per_sqm REAL NOT NULL
        )
    ''')

    # Создание объединённой таблицы
    conn.execute('''
        CREATE TABLE IF NOT EXISTS combined_services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            price_per_sqm REAL NOT NULL,
            total_area REAL NOT NULL,
            service_cost REAL NOT NULL
        )
    ''')

    # Заполнение таблицы с услугами, если она пуста
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM services")
    if cursor.fetchone()[0] == 0:
        # Данные для таблицы услуг
        services_data = [
            ("Настил линолеума", 350.00),
            ("Укладка ламината/паркета по диагонали", 400.00),
            ("Укладка ламината/паркета по горизонтали", 300.00),
            ("Укладка плитки/керамогранита по полу", 1000.00),
            ("Устройство подвесных потолков", 1500.00),
            ("Устройство натяжного потолка", 2000.00),
            ("Покраска потолка", 250.00),
            ("Отделка стен тканью", 1000.00),
            ("Покраска стен", 300.00),
            ("Поклейка обоев", 200.00),
            ("Укладка плитки/керамогранита по стенам", 850.00),
        ]

        # Заполняем таблицу данными
        cursor.executemany('''
                INSERT INTO services (service_name, price_per_sqm)
                VALUES (?, ?)
                ''', services_data)

conn.commit()

#Обработчик кнопки site
@bot.message_handler(commands=['site'])
def start(message):
    bot.send_message(message.chat.id, "В ближайшем будущем сайт будет реализован")

#Обработчик кнопки start
@bot.message_handler(commands=['start'])
def start(message):
    welcome_text = (
        "Привет! Я помогу вам рассчитать примерную стоимость ремонта для квартиры, дома или коммерческой недвижимости.\n\n"
        "Выберите пункт из меню ниже:"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Рассчитать стоимость ремонта", callback_data="calculate"))
    markup.row(
        types.InlineKeyboardButton("Цены", callback_data="prices"),
        types.InlineKeyboardButton("Наши работы", callback_data="our_works")
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)


# Обработчик кнопок
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "calculate":
        with sqlite3.connect('construction_services.db') as conn:
            cursor = conn.cursor()

            # Очистка данных из таблицы objects
            cursor.execute('DELETE FROM objects')
            conn.commit()

            # Очистка данных из таблицы combined_services
            cursor.execute('DELETE FROM combined_services')
            conn.commit()

        bot.send_message(call.message.chat.id, "Какая длина пола?")
        bot.register_next_step_handler(call.message, get_floor_length)

    elif call.data == "prices":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Вернуться в главное меню", callback_data="main_menu"))
        bot.send_message(
            call.message.chat.id,
            "Ознакомьтесь с актуальными ценами: [Ремонтстрой_Цены_работ.xlsx](https://disk.yandex.ru/i/wv2ghnXLlbINZA)",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif call.data == "our_works":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Вернуться в главное меню", callback_data="main_menu"))
        bot.send_message(
            call.message.chat.id,
            "Посмотрите примеры наших выполненных проектов на Яндекс.Диске: [Наши работы на Яндекс.Диск](https://disk.yandex.ru/a/IJ5ZrWve7X2-PQ)",
            parse_mode="Markdown",
            reply_markup=markup
        )

    elif call.data == "main_menu":
        start(call.message)

    elif call.data == "edit_area":
        ask_area_update(call.message.chat.id)
    elif call.data == "continue_floor":
        ask_floor_update(call.message.chat.id)


    elif call.data == "update_floor_length":
        bot.send_message(call.message.chat.id, "Введите новую длину пола:")
        bot.register_next_step_handler(call.message, update_floor_length)
    elif call.data == "update_floor_width":
        bot.send_message(call.message.chat.id, "Введите новую ширину пола:")
        bot.register_next_step_handler(call.message, update_floor_width)
    elif call.data == "update_room_height":
        bot.send_message(call.message.chat.id, "Введите новую высоту комнаты:")
        bot.register_next_step_handler(call.message, update_room_height)
    elif call.data == "update_window_area":
        bot.send_message(call.message.chat.id, "Введите новую площадь окон:")
        bot.register_next_step_handler(call.message, update_window_area)


    elif call.data == "update_floor_yes":
        floor_menu(call.message.chat.id)
    elif call.data == "update_floor_no":
        ask_ceiling_update(call.message.chat.id)
    elif call.data.startswith("floor_"):
        type = call.data.split("_")[0]
        work = call.data.split("_")[1]
        user_id = call.from_user.id
        if work == "linoleum":
            work_name = "Настил линолеума"
            save_flour_or_celling_to_db(call, user_id, work_name, type)
        elif work == "diag":
            work_name = "Укладка ламината/паркета по диагонали"
            save_flour_or_celling_to_db(call, user_id, work_name, type)
        elif work == "horiz":
            work_name = "Укладка ламината/паркета по горизонтали"
            save_flour_or_celling_to_db(call, user_id, work_name, type)
        elif work == "tile":
            work_name = "Укладка плитки/керамогранита по полу"
            save_flour_or_celling_to_db(call, user_id, work_name, type)

    elif call.data == "service_skip_floor":
        ask_ceiling_update(call.message.chat.id)



    elif call.data == "update_ceiling_yes":
        ceiling_menu(call.message.chat.id)
    elif call.data == "update_ceiling_no":
        ask_wall_update(call.message.chat.id)
    elif call.data.startswith("ceiling_"):
        type = call.data.split("_")[0]
        work = call.data.split("_")[1]
        user_id = call.from_user.id
        if work == "suspended":
            work_name = "Устройство подвесных потолков"
            save_flour_or_celling_to_db(call, user_id, work_name, type)
        elif work == "stretch":
            work_name = "Устройство натяжного потолка"
            save_flour_or_celling_to_db(call, user_id, work_name, type)
        elif work == "paint":
            work_name = "Покраска потолка"
            save_flour_or_celling_to_db(call, user_id, work_name, type)

    elif call.data == "service_skip_ceiling":
        ask_wall_update(call.message.chat.id)


    elif call.data == "update_walls_yes":
        wall_menu(call.message.chat.id)
    elif call.data == "update_walls_no":
        handle_service_skip_wall(call)

    elif call.data.startswith("wall_"):
        work = call.data.split("_")[1]
        user_id = call.from_user.id
        if work == "fabric":
            work_name = "Отделка стен тканью"
            save_wall_to_db(call, user_id, work_name)
        elif work == "paint":
            work_name = "Покраска стен"
            save_wall_to_db(call, user_id, work_name)
        elif work == "wallpaper":
            work_name = "Поклейка обой"
            save_wall_to_db(call, user_id, work_name)
        elif work == "tile":
            work_name = "Укладка плитки/керамогранита по стенам"
            save_wall_to_db(call, user_id, work_name)

    elif call.data == "service_skip_wall":
        handle_service_skip_wall(call)

#Функция для запроса ширины
def get_floor_length(message):
    user_id = message.from_user.id
    user_data.setdefault(user_id, {})["floor_length"] = float(message.text)
    bot.send_message(message.chat.id, "Какая ширина пола?")
    bot.register_next_step_handler(message, get_floor_width)

#Функция для запроса высоты комнаты
def get_floor_width(message):
    user_id = message.from_user.id
    user_data[user_id]["floor_width"] = float(message.text)
    bot.send_message(message.chat.id, "Какая высота комнаты?")
    bot.register_next_step_handler(message, get_room_height)


# Запрос площади окна
def get_room_height(message):
    user_id = message.from_user.id
    user_data[user_id]["room_height"] = float(message.text)
    bot.send_message(message.chat.id, "Какая общая площадь окон в комнате?")
    bot.register_next_step_handler(message, get_window_area)


# Сохранение площади окна и вывод площадей пользователю
def get_window_area(message):
    user_id = message.from_user.id
    user_data[user_id]["window_area"] = float(message.text)

    # Рассчитываем площади
    floor_area = user_data[user_id]["floor_length"] * user_data[user_id]["floor_width"]
    wall_area = (
                        2 * user_data[user_id]["room_height"] * user_data[user_id]["floor_length"] +
                        2 * user_data[user_id]["room_height"] * user_data[user_id]["floor_width"]
                ) - user_data[user_id]["window_area"]

    user_data[user_id]["floor_area"] = floor_area
    user_data[user_id]["wall_area"] = wall_area

    # Сохраняем данные в базу, включая user_id
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO objects (user_id, floor_length, floor_width, room_height, window_area)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            user_id,  # Сохраняем user_id
            user_data[user_id]["floor_length"],
            user_data[user_id]["floor_width"],
            user_data[user_id]["room_height"],
            user_data[user_id]["window_area"]
        ))
        conn.commit()

    bot.send_message(
        message.chat.id,
        f"S - обозначение площади.\n\n"
        f"S пола / потолка = {floor_area:.2f} м²\n"
        f"S стен = {wall_area:.2f} м²"
    )
    ask_next_step(message.chat.id)

#Функция запроса параметра
def ask_next_step(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Изменить неверно введенный параметр", callback_data="edit_area"))
    markup.add(types.InlineKeyboardButton("Продолжить", callback_data="continue_floor"))
    bot.send_message(chat_id, "Что вы хотите сделать дальше?", reply_markup=markup)


#Функция замены введенной длины пола
def update_floor_length(message):
    user_id = message.from_user.id
    new_length = float(message.text)
    user_data[user_id]["floor_length"] = new_length

    # Обновляем в базе
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE objects
            SET floor_length = ?
            WHERE id = (
                SELECT MAX(id) FROM objects
            )
        ''', (new_length,))
        conn.commit()

    bot.send_message(message.chat.id, f"Длина пола обновлена на {new_length:.2f} м.")
    recalculate_areas(message)

#Функция замены введенной ширины пола
def update_floor_width(message):
    user_id = message.from_user.id
    new_width = float(message.text)
    user_data[user_id]["floor_width"] = new_width

    # Обновляем в базе
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE objects
            SET floor_width = ?
            WHERE id = (
                SELECT MAX(id) FROM objects
            )
        ''', (new_width,))
        conn.commit()

    bot.send_message(message.chat.id, f"Ширина пола обновлена на {new_width:.2f} м.")
    recalculate_areas(message)

#Функция замены введенной высоты комнаты
def update_room_height(message):
    user_id = message.from_user.id
    new_height = float(message.text)
    user_data[user_id]["room_height"] = new_height

    # Обновляем в базе
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE objects
            SET room_height = ?
            WHERE id = (
                SELECT MAX(id) FROM objects
            )
        ''', (new_height,))
        conn.commit()

    bot.send_message(message.chat.id, f"Высота комнаты обновлена на {new_height:.2f} м.")
    recalculate_areas(message)

#Функция замены введенной площади окна
def update_window_area(message):
    user_id = message.from_user.id
    new_window_area = float(message.text)
    user_data[user_id]["window_area"] = new_window_area

    # Обновляем в базе
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE objects
            SET window_area = ?
            WHERE id = (
                SELECT MAX(id) FROM objects
            )
        ''', (new_window_area,))
        conn.commit()

    bot.send_message(message.chat.id, f"Площадь окон обновлена на {new_window_area:.2f} м².")
    recalculate_areas(message)

#Функция перерасчета площадей
def recalculate_areas(message):
    user_id = message.from_user.id
    floor_area = user_data[user_id]["floor_length"] * user_data[user_id]["floor_width"]
    wall_area = (
                        2 * user_data[user_id]["room_height"] * user_data[user_id]["floor_length"] +
                        2 * user_data[user_id]["room_height"] * user_data[user_id]["floor_width"]
                ) - user_data[user_id]["window_area"]

    user_data[user_id]["floor_area"] = floor_area
    user_data[user_id]["wall_area"] = wall_area

    bot.send_message(
        message.chat.id,
        f"Пересчитанные площади:\n\n"
        f"S пола / потолка = {floor_area:.2f} м²\n"
        f"S стен = {wall_area:.2f} м²"
    )
    ask_area_update(message.chat.id)

#Функция запроса параметра
def ask_area_update(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Изменить длину пола", callback_data="update_floor_length"))
    markup.add(types.InlineKeyboardButton("Изменить ширину пола", callback_data="update_floor_width"))
    markup.add(types.InlineKeyboardButton("Изменить высоту комнаты", callback_data="update_room_height"))
    markup.add(types.InlineKeyboardButton("Изменить площадь окон", callback_data="update_window_area"))
    markup.add(types.InlineKeyboardButton("Продолжить", callback_data="continue_floor"))
    bot.send_message(chat_id, "Какой параметр вы хотите изменить?", reply_markup=markup)


# Работа с полом и потолком
# Функция запроса работы по полу
def ask_floor_update(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Да", callback_data="update_floor_yes"))
    markup.add(types.InlineKeyboardButton("Нет", callback_data="update_floor_no"))
    bot.send_message(chat_id, "Вы хотите сделать работы по полу?", reply_markup=markup)


# Функция отображения меню выбора работы по полу
def floor_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Настил линолеума", callback_data="floor_linoleum")),
    markup.add(types.InlineKeyboardButton("Укладка ламината (по диагонали)", callback_data="floor_diag"))
    markup.add(types.InlineKeyboardButton("Укладка ламината (по горизонтали)", callback_data="floor_horiz")),
    markup.add(types.InlineKeyboardButton("Укладка плитки", callback_data="floor_tile"))
    markup.add(types.InlineKeyboardButton("Пропустить", callback_data="service_skip_floor"))
    bot.send_message(chat_id, "Какая работа вас интересует?", reply_markup=markup)

# Работа с полом и потолком
# Функция записи услиги работы с полом и потолком в базу данных
def save_flour_or_celling_to_db(call, user_id, work_name, type):
    # Получаем данные о площади из таблицы объектов
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()

        # Извлекаем данные для конкретного пользователя
        cursor.execute(''' 
            SELECT floor_length, floor_width FROM objects WHERE user_id = ?
        ''', (user_id,))
        object_data = cursor.fetchone()

        if object_data:
            floor_length, floor_width = object_data
            floor_area = floor_length * floor_width
        else:
            bot.send_message(call.message.chat.id, "Не удалось найти данные о площади. Попробуйте еще раз.")
            return

        # Получаем цену услуги из таблицы услуг
        cursor.execute('''
            SELECT price_per_sqm FROM services WHERE service_name = ?
        ''', (work_name,))
        price_per_sqm = cursor.fetchone()

        if price_per_sqm:
            price_per_sqm = price_per_sqm[0]
        else:
            bot.send_message(call.message.chat.id, "Услуга не найдена. Попробуйте выбрать другую работу.")
            return

        service_cost = price_per_sqm * floor_area

        # Вставляем данные в объединенную таблицу
        cursor.execute('''
            INSERT INTO combined_services (service_name, price_per_sqm, total_area, service_cost)
            VALUES (?, ?, ?, ?)
        ''', (
            work_name,
            price_per_sqm,
            floor_area,
            service_cost
        ))
        conn.commit()

    # Отправляем итоговую стоимость пользователю
    bot.send_message(call.message.chat.id, f"Вы выбрали: {work_name}\nИтоговая стоимость: {service_cost:.2f} ₽")

    if type == "floor":
        ask_ceiling_update(call.message.chat.id)
    elif type == "ceiling":
        ask_wall_update(call.message.chat.id)

#Функция записи услиги работы со стенами в базу данных
def save_wall_to_db(call, user_id, work_name):
    # Получаем данные о площади из таблицы объектов
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()

        # Извлекаем данные для конкретного пользователя
        cursor.execute(''' 
            SELECT floor_length, floor_width, room_height, window_area  FROM objects WHERE user_id = ?
        ''', (user_id,))
        object_data = cursor.fetchone()

        if object_data:
            floor_length, floor_width, room_height, window_area = object_data
            wall_area = ((floor_length + floor_width) * 2) * room_height - window_area
        else:
            bot.send_message(call.message.chat.id, "Не удалось найти данные о площади. Попробуйте еще раз.")
            return

        # Получаем цену услуги из таблицы услуг
        cursor.execute('''
            SELECT price_per_sqm FROM services WHERE service_name = ?
        ''', (work_name,))
        price_per_sqm = cursor.fetchone()

        if price_per_sqm:
            price_per_sqm = price_per_sqm[0]
        else:
            bot.send_message(call.message.chat.id, "Услуга не найдена. Попробуйте выбрать другую работу.")
            return

        service_cost = price_per_sqm * wall_area

        # Вставляем данные в объединенную таблицу
        cursor.execute('''
            INSERT INTO combined_services (service_name, price_per_sqm, total_area, service_cost)
            VALUES (?, ?, ?, ?)
        ''', (
            work_name,
            price_per_sqm,
            wall_area,
            service_cost
        ))
        conn.commit()

    # Отправляем итоговую стоимость пользователю
    bot.send_message(call.message.chat.id, f"Вы выбрали: {work_name}\nИтоговая стоимость: {service_cost:.2f} ₽")
    handle_service_skip_wall(call)

# Функция запроса работы по потолку
def ask_ceiling_update(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Да", callback_data="update_ceiling_yes"))
    markup.add(types.InlineKeyboardButton("Нет", callback_data="update_ceiling_no"))
    bot.send_message(chat_id, "Вы хотите сделать работы по потолку?", reply_markup=markup)

# Функция отображения меню выбора работы по потолку
def ceiling_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Устройство подвесных потолков", callback_data="ceiling_suspended"))
    markup.add(types.InlineKeyboardButton("Устройство натяжного потолка", callback_data="ceiling_stretch"))
    markup.add(types.InlineKeyboardButton("Покраска потолка", callback_data="ceiling_paint"))
    markup.add(types.InlineKeyboardButton("Пропустить", callback_data="service_skip_ceiling"))
    bot.send_message(chat_id, "Какая работа вас интересует?", reply_markup=markup)

# Функция запроса работы по стенам
def ask_wall_update(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Да", callback_data="update_walls_yes"))
    markup.add(types.InlineKeyboardButton("Нет", callback_data="update_walls_no"))
    bot.send_message(chat_id, "Вы хотите сделать работы по стенам?", reply_markup=markup)

# Функция отображения меню выбора работы по стенам
def wall_menu(chat_id):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Отделка стен тканью", callback_data="wall_fabric"))
    markup.add(types.InlineKeyboardButton("Покраска стен", callback_data="wall_paint"))
    markup.add(types.InlineKeyboardButton("Поклейка обой", callback_data="wall_wallpaper"))
    markup.add(types.InlineKeyboardButton("Укладка плитки/керамогранита по стенам", callback_data="wall_tile"))
    markup.add(types.InlineKeyboardButton("Пропустить", callback_data="service_skip_wall"))
    bot.send_message(chat_id, "Какая работа вас интересует?", reply_markup=markup)

# Функция вывода данных в эксель
def handle_service_skip_wall(call):
    with sqlite3.connect('construction_services.db') as conn:
        cursor = conn.cursor()

        # Извлечение всех записей из таблицы combined_services
        cursor.execute('SELECT id, service_name, price_per_sqm, total_area, service_cost FROM combined_services')
        services = cursor.fetchall()

        if not services:
            bot.send_message(call.message.chat.id, "Нет данных о предоставленных услугах.\n\n"
                                                   "Пожалуйста, начните с расчета заново.")
            # Отправка кнопки для начала нового расчета
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Начать заново", callback_data="calculate"))
            bot.send_message(call.message.chat.id, "Нажмите на кнопку ниже, чтобы начать:", reply_markup=markup)
            return

        # Формирование сообщения со списком услуг
        services_list = "Список услуг:\n\n"
        total_cost = 0

        for service in services:
            service_id, service_name, price_per_sqm, total_area, service_cost = service
            services_list += (
                f"№{service_id}: {service_name}\n"
                f"Цена за 1 кв.м: {price_per_sqm:.2f} ₽\n"
                f"Количество кв.м: {total_area:.2f}\n"
                f"Стоимость: {service_cost:.2f} ₽\n\n"
            )
            total_cost += service_cost

        # Отправка списка услуг
        bot.send_message(call.message.chat.id, services_list)

        # Отправка сообщения с общей суммой
        bot.send_message(call.message.chat.id, f"Общая стоимость всех услуг: {total_cost:.2f} ₽")

        # Экспорт данных в Excel
        df = pd.DataFrame(services, columns=["ID", "Название услуги", "Цена за кв.м", "Площадь (кв.м)", "Стоимость"])
        excel_file_path = "combined_services.xlsx"
        df.to_excel(excel_file_path, index=False)

        # Отправка файла пользователю
        with open(excel_file_path, "rb") as file:
            bot.send_document(call.message.chat.id, file)



bot.polling(none_stop=True)
