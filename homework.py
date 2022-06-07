import logging
import os
import sys
import requests
import time
from http import HTTPStatus
from dotenv import load_dotenv
from telegram import Bot

from exceptions import (
    EndpointNotAvailable,
    HTTPStatusNotOK,
    UnknownHomeworkStatus
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
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


logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler(sys.stdout))


def send_message(bot, message) -> None:
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(f"Сообщение '{message}' в чат успешно отправлено")
    except Exception as error:
        logger.error(f'Ошибка при отправка сообщения {message}: {error}')


def get_api_answer(current_timestamp) -> dict:
    """Осуществление запроса к эндпоинту API-сервиса Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            params=params,
            headers=HEADERS,
        )
    except Exception as error:
        message = f'Ошибка при осуществлении запроса к эндпоинту: {error}'
        raise EndpointNotAvailable(message)
    response_status = response.status_code
    if response_status != HTTPStatus.OK:
        message = f'Эндпоинт недоступен, статус: {response_status}'
        raise HTTPStatusNotOK(message)
    response = response.json()
    return response


def check_response(response) -> list:
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError(
            'Ответ API не содержит сведений о домашних работах'
        )
    current_date = response.get('current_date')
    if current_date is None:
        raise KeyError('Ответ API не содержит сведений о времени запроса')
    if not isinstance(homeworks, list):
        raise TypeError(
            "Содержимое ответа по ключу 'homeworks' не является списком"
        )
    if not isinstance(current_date, int):
        raise TypeError(
            "Содержимое ответа по ключу 'current_date' не является int"
        )
    logging.info('Проверка ответа API на корректность пройдена.')
    return homeworks


def parse_status(homework) -> str:
    """Извлечение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    if homework_name is None:
        raise KeyError('Отсутствует имя домашней работы в ответе API')
    homework_status = homework.get('status')
    if homework_status is None:
        raise KeyError('Отсутствует статус домашней работы в ответе API')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise UnknownHomeworkStatus(
            f'Неизвестный статус домашней работы: {homework_status}'
        )
    logger.info('Статус домашней работы извлечен')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token in tokens:
        if not tokens[token]:
            logger.critical(
                f'Отсутствие обязательной переменной окружения: {token}'
            )
            return False
    logging.info('Проверка доступности переменных окружения пройдена.')
    return True


def main() -> None:
    """Основная логика работы бота."""
    PREVIOUS_ERROR = ''
    logger.info('Начало работы телеграм-бота')
    if not check_tokens():
        logger.info('Принудительная остановка работы телеграм-бота')
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_list = check_response(response)
            if len(homeworks_list) > 0:
                for homework in homeworks_list:
                    status_msg = parse_status(homework)
                    send_message(bot, status_msg)
            else:
                logger.debug(
                    'Новых записей о статусах домашних работ не найдено'
                )
            current_timestamp = response.get(
                'current_date',
                int(time.time())
            )
        except Exception as error:
            message = f'Ошибка в работе: {error}'
            logger.error(message)
            if error != PREVIOUS_ERROR:
                PREVIOUS_ERROR = error
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        handlers=[logging.FileHandler(
            'main.log',
            mode='w',
            encoding='UTF-8')]
    )
    main()
