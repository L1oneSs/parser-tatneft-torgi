import httpx
from bs4 import BeautifulSoup
import pandas as pd
import telebot
from telebot import types
from config import BOT_TOKEN

TOKEN = BOT_TOKEN
bot = telebot.TeleBot(TOKEN)

# Глобальная переменная для хранения ID сообщений
messages = []


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2)
    btn_get_data = types.KeyboardButton('Получить данные')
    btn_clear_chat = types.KeyboardButton('Очистить чат')
    markup.add(btn_get_data, btn_clear_chat)
    bot.reply_to(message, "Привет! Нажмите 'Получить данные', чтобы получить информацию, или 'Очистить чат', чтобы удалить сообщения.", reply_markup=markup)


# Обработчик кнопки "Получить данные"
@bot.message_handler(func=lambda message: message.text == 'Получить данные')
def fetch_data(message):
    url = 'https://torgi.tatneft.ru/torgi/'

    # Выполние запроса с отключением проверки SSL
    try:
        response = httpx.get(url, verify=False)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')

            table = soup.find('table', class_='lot-list-table')

            if table:
                headers = [th.get_text(strip=True) for th in table.find('tr').find_all('th')]
                headers.append('Ссылка')

                data = []

                rows = table.find_all('tr', class_='lot-list-row')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) == 8:
                        number = cols[0].get_text(strip=True)
                        category = cols[1].get_text(strip=True)
                        title_tag = cols[2].find('a')
                        title = title_tag.get_text(strip=True)
                        link = title_tag['href'] if title_tag else ''
                        status = cols[3].get_text(strip=True)
                        publish_date = cols[4].get_text(strip=True)
                        start_price = cols[5].get_text(strip=True)
                        start_date = cols[6].get_text(strip=True)
                        end_date = cols[7].get_text(strip=True)

                        if category == 'Транспортные средства' and status.lower() != 'торги завершены':
                            data.append(
                                [number, category, title, status, publish_date, start_price, start_date, end_date,
                                 link])

                df = pd.DataFrame(data, columns=headers)

                global messages
                messages = []  # Очистка списка сообщений перед отправкой новых

                for index, row in df.iterrows():
                    number = row['№']
                    auto = row['Наименование'].split(',')[0]
                    reg_number = row['Наименование'].split('рег. номер ')[1] if 'рег. номер ' in row[
                        'Наименование'] else 'Не указан'
                    status = row['Состояние']
                    publish_date = row['Дата публикации']
                    start_date = row['Начало']
                    end_date = row['Окончание']
                    link = row['Ссылка']

                    message_text = (
                        f"🚗 Автомобиль: {auto}\n"
                        f"🔎 Рег.Номер: {reg_number}\n\n"
                        f"🔢 № Лота: {number}\n"
                        f"📊 Статус торгов: {status}\n"
                        f"📅 Дата публикации: {publish_date}\n"
                        f"🕒 Начало: {start_date}\n"
                        f"🕛 Окончание: {end_date}\n"
                        f"🔗 Ссылка: https://torgi.tatneft.ru/torgi/{link}"
                    )

                    sent_message = bot.send_message(message.chat.id, message_text)
                    messages.append(sent_message.message_id)  # Сохрание ID сообщения

            else:
                bot.send_message(message.chat.id, "Таблица с классом 'lot-list-table' не найдена")
        else:
            bot.send_message(message.chat.id, f"Ошибка доступа к сайту: {response.status_code}")
    except httpx.HTTPStatusError as exc:
        bot.send_message(message.chat.id, f"Ошибка HTTP: {exc}")


# Обработчик кнопки "Очистить чат"
@bot.message_handler(func=lambda message: message.text == 'Очистить чат')
def clear_chat(message):

    global messages
    for msg_id in messages:
        try:
            bot.delete_message(message.chat.id, msg_id)
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")
    messages = []  # Очистка списка после удаления сообщений


bot.polling(none_stop=True)
