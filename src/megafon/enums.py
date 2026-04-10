"""
Модуль с перечислениями для работы с API Мегафон.

Содержит наборы разрешенных cookies для различных типов запросов к API.
"""
from enum import Enum


class AllowedCookies(Enum):
    """
    Перечисление разрешенных cookies для различных операций API.

    Определяет, какие cookies должны быть включены в запросы
    для различных типов операций с API Мегафон.
    """
    CHECK_SESSION = [
        "ADDITIONAL_USER_GUID",
        "JSESSIONID",
        "USER-GUID",
        "X-Cabinet-Refresh-Token",
        "_ym_isad",
        "_ym_d",
        "_ym_uid",
    ]
    REFRESH_TOKEN = [
        "X-Cabinet-Refresh-Token",
        "ADDITIONAL_USER_GUID",
        "USER-GUID",
        "_ym_isad",
        " _ym_d",
        "_ym_uid",
    ]
    PUSH_PIN = [
        "JSESSIONID",
        "ADDITIONAL_USER_GUID",
        "USER-GUID",
        "_ym_isad",
        " _ym_d",
        "_ym_uid",
    ]
