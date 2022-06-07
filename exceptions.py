class EndpointNotAvailable(Exception):
    """Ошибка при осуществлении запроса к эндпоинту."""


class HTTPStatusNotOK(Exception):
    """Эндпоинт недоступен."""


class UnknownHomeworkStatus(Exception):
    """Неизвестный статус домашней работы."""

