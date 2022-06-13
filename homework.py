import logging
import sys
import requests
import time
from telegram import Bot

from logger import set_logging

from config import (
    RETRY_TIME,
    HOST,
    HEADERS,
    HOMEWORK_STATUSES,
    HTTP_STATUSES_URL
)

from env_vars import (
    PRACTICUM_TOKEN,
    TELEGRAM_TOKEN,
    TELEGRAM_CHAT_ID
)

from exceptions import (
    EndpointNotAvailable,
    UnknownHomeworkStatus,
)


logger = logging.getLogger(__name__)


def send_message(bot, message) -> None:
    """Отправка сообщения в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Сообщение успешно отправлено в чат {TELEGRAM_CHAT_ID}')
    except Exception as error:
        logger.error(f'Ошибка при отправка сообщения {message}: {error}')


def get_api_answer(current_timestamp) -> dict:
    """Осуществление запроса к эндпоинту API-сервиса Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    api_var = 'user_api/homework_statuses/'
    endpoint = HOST + api_var
    try:
        response = requests.get(
            endpoint,
            params=params,
            headers=HEADERS,
        )
    except requests.exceptions.RequestException as error:
        message = f'Ошибка при осуществлении запроса к эндпоинту: {error}'
        raise EndpointNotAvailable(message)
    http_error_msg = ''
    response_status = response.status_code
    if 400 <= response_status < 500:
        http_error_msg = (
            f'Ошибка клиента. Код: {response_status}. '
            f'Подробнее: {HTTP_STATUSES_URL}{response_status}'
        )
    elif 500 <= response_status < 600:
        http_error_msg = (
            f'Ошибка сервера. Код: {response_status}. '
            f'Подробнее: {HTTP_STATUSES_URL}{response_status}'
        )
    if http_error_msg:
        raise requests.exceptions.HTTPError(http_error_msg, response=response)
    try:
        response = response.json()
    except Exception as error:
        message = f'Ошибка трансформации ответа в формат json: {error}'
        raise requests.exceptions.InvalidJSONError(message)
    logging.info('Запрос к эндпоинту осуществлен успешно.')
    return response


def check_response(response) -> list:
    """Проверка ответа API на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API не является словарем')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError(
            'Ответ API не содержит сведений о домашних работах. '
            'Содержимое ответа API: ', response
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
    set_logging()
    main()
