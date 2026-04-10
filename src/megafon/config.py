"""
Модуль конфигурации для работы с API Мегафон.

Содержит константы, заголовки HTTP-запросов и настройки по умолчанию
для взаимодействия с API Мегафон.
"""

#: Задержка по умолчанию между запросами (в секундах)
DEFAULT_DELAY = 1

#: PIN-код по умолчанию для операций
DEFAULT_PIN_CODE = "0000"

#: Стоимость одного номера в рублях
ONE_NUMBER_PRICE = 30

#: Базовые заголовки для запросов к API Мегафон
BASE_HEADERS = {
    "Host": "api.megafon.ru",
    "Accept": "application/json, text/plain, */*",
    "X-App-Type": "external",
    "X-Mlk-Device": "iPhone13,2",
    "X-Mlk-Device-Id": "B939C0C7-065D-4248-BD85-64BA79BE44EE",
    "Accept-Language": "ru",
    "Origin": "https://lk.megafon.ru",
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_3_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Referer": "https://lk.megafon.ru/?appType=external",
    "X-Cabinet-User-Agent": "NLK iOS Phone 4.62.0",
    "X-Mlk-Os-Version": "iOS-16.3.1",
}

#: Базовые заголовки для запросов аутентификации
BASE_AUTH_HEADERS = {
    "Host": "api.megafon.ru",
    "Accept": "application/json",
    "X-Mlk-Device": "iPhone13,2",
    "X-Cabinet-Screen-Id": "null",
    "Accept-Language": "ru",
    "User-Agent": "NLK iOS Phone 4.62.0",
    "X-Mlk-Screen-Id": "StartViewController",
    "X-Mlk-Os-Version": "iOS-16.3.1",
    "X-Cabinet-Capabilities": "rw-refresh-token-2022",
    "X-Mlk-Device-Id": "62BE64D0-2CE5-429C-81DD-E5EFD24B91D6",
}
