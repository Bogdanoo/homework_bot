import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import RequestException
from http import HTTPStatus

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
    """Отправляет сообщение в Telegram чат.
    Определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра:
    экземпляр класса Bot и строку с текстом сообщения
    """
    try:
        logging.info(f'Message sent')
        return bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except RequestException:
        logging.error('Telegram problem', exc_info=True)
        raise Exception('Ошибка приложения Телеграм')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса.
    Преобразование ответа API из формата JSON к типам данных Python.
    """
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        logging.info('Server response')
        if homework_statuses.status_code != HTTPStatus.OK:
            raise Exception('Error')
        return homework_statuses.json()
    except Exception:
        logging.error('Invalid response')
        raise Exception('Упс, что то пошло не так')


def check_response(response):
    """Проверяет ответ API на корректность.
    Функция должна вернуть список домашних работ
    (он может быть и пустым), доступный в ответе API по ключу 'homeworks'.
    """
    if not isinstance(response['homeworks'], list):
        raise Exception('Некорректный ответ сервера')
    return response['homeworks']


def parse_status(homework):
    """Извлекает нужную информацию о статусе работы.
    Функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_STATUSES.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        raise Exception('Статус не существует!')
    verdict = HOMEWORK_STATUSES[homework_status]
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
    current_timestamp = int(time.time() - 604800)
    previous_status = None
    while True:
        logging.debug('Bot is running')
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            homework_status = homeworks[0].get('status')
            if homework_status != previous_status:
                previous_status = homework_status
                message = parse_status(homeworks[0])
                send_message(bot, message)
            current_timestamp = int(time.time())
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error('Failure')
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
