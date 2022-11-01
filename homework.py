import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(name), %(message)s',
    filemode='a'
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('AUTH_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат
    Определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        logging.info(f'Message sent: {message}')
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except RequestException:
        logging.error('Telegram problem', exc_info=True)
        return 'Ошибка приложения Телеграм'


def get_api_answer(url, current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    Преобразование ответа API из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            url,
            headers=HEADERS,
            params=params
        )
        logging.info('Server response')
        if homework_statuses.status_code != 200:
            raise Exception('Error')
        return homework_statuses.json()
    except RequestException:
        logging.error('Invalid response')
        return 'Упс, что то пошло не так'


def check_response(response):
    """Проверяет ответ API на корректность.
    Функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'.
    """
    homeworks = response.get('homeworks')
    if not homeworks:
        raise Exception('Домашней работы не существует!')
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES:
            return homework
        raise Exception('Статус не существует!')


def parse_status(homework):
    """Извлекает нужную информацию о статусе работы.
    Функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework.get('homework_name')
    if homework_name is None:
        error_message = 'Homework name not exist'
        logging.error(error_message)
        return error_message
    homework_status = homework.get('homework_status')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError:
        logging.error(f'No such status: {homework_status}')
        return 'Ошибка получения статуса'
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения.
    Если отсутствует хотя бы одна переменная окружения —
    функция должна вернуть False, иначе — True.
        """
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        logging.debug('Bot is running')
        try:
            response = check_response(
                get_api_answer(
                    ENDPOINT,
                    current_timestamp
                ))
            if response:
                parsing = parse_status(response)
                send_message(bot, parsing)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error('Failure')
            time.sleep(RETRY_TIME)
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
