from env_vars import PRACTICUM_TOKEN
from urllib.parse import quote

RETRY_TIME = 600
HOST = 'https://practicum.yandex.ru/api/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HTTP_STATUSES_URL = (
    'https://ru.wikipedia.org/wiki/' +
    quote('Список_кодов_состояния_HTTP') + '#'
)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}
