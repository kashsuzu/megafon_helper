"""
Модуль с исключениями для работы с API Мегафон.

Содержит иерархию исключений для обработки различных ошибок
при взаимодействии с API Мегафон и процессом аутентификации.
"""


class BaseError(Exception):
    """Базовое исключение для всех ошибок модуля."""
    pass


class MegafonAPIError(Exception):
    """Базовое исключение для ошибок API Мегафон."""
    pass


class RefreshTokenUpdateFailed(MegafonAPIError):
    """Исключение при неудачном обновлении refresh token."""
    pass


class NeedRefreshTokenError(MegafonAPIError):
    """Исключение, сигнализирующее о необходимости обновить токен."""
    pass


class NeedRequestRepeatError(MegafonAPIError):
    """Исключение, сигнализирующее о необходимости повторить запрос."""
    pass


class NeedCheckSession(MegafonAPIError):
    """Исключение, сигнализирующее о необходимости проверить сессию."""
    pass


class NeedAuthError(MegafonAPIError):
    """Исключение, сигнализирующее о необходимости повторной аутентификации."""
    pass


class ServiceAvailabilityError(MegafonAPIError):
    """Исключение при недоступности сервиса Мегафон."""
    pass


class MegafonAuthAPIError(BaseError):
    """Базовое исключение для ошибок аутентификации в API Мегафон."""
    pass


class IncorrectOTPCode(MegafonAuthAPIError):
    """Исключение при вводе неверного OTP-кода."""
    pass
