"""
Модуль HTTP-клиента для работы с API Мегафон.

Содержит класс MegafonHTTPClient для выполнения HTTP-запросов
с автоматической обработкой ошибок, повторными попытками и
управлением cookies и заголовками.
"""
import asyncio
from typing import NoReturn

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout
from config import USE_DELAY
from loguru import logger

from src.megafon.config import BASE_AUTH_HEADERS, DEFAULT_DELAY
from src.megafon.datatypes import Response
from src.megafon.exceptions import MegafonAPIError, NeedCheckSession

from .account import MegafonAccount


def retrier(max_attempts: int = 3):
    """
    Декоратор для повторных попыток выполнения запроса при ошибках.

    :param max_attempts: Максимальное количество попыток
    :return: Декорированная функция с логикой повторных попыток
    """
    def wrapper(func):
        async def inner(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except (ClientError, asyncio.TimeoutError) as err:
                    logger.warning(
                        f"⚠️ Попытка {attempt}/{max_attempts} завершилась ошибкой: {err}"
                    )

                    if attempt == max_attempts:
                        logger.error(
                            "❌ Превышено максимальное количество попыток запроса"
                        )
                    raise err

        return inner

    return wrapper


class MegafonHTTPClient:
    """
    HTTP-клиент для взаимодействия с API Мегафон.

    Предоставляет методы для выполнения HTTP-запросов с автоматической
    обработкой заголовков, cookies, ошибок и повторными попытками.
    """

    def __init__(self, account: MegafonAccount) -> None:
        """
        Инициализация HTTP-клиента.

        :param account: Аккаунт Мегафон для выполнения запросов
        """
        self.account = account

    def _prepare_headers(
        self, headers: dict = {}, use_strict_headers: bool = False
    ) -> dict:
        """
        Подготавливает заголовки для запроса.

        :param headers: Дополнительные заголовки
        :param use_strict_headers: Использовать только переданные заголовки
        :return: Полный набор заголовков для запроса
        """
        if use_strict_headers:
            return headers

        return headers | BASE_AUTH_HEADERS

    def _proccess_cookies(
        self,
        cookies: dict,
        exclude_cookies: list[str],
        allowed_cookies: list[str],
    ) -> dict:
        """
        Обрабатывает cookies для запроса.

        :param cookies: Словарь cookies
        :param exclude_cookies: Список cookies для исключения
        :param allowed_cookies: Список разрешенных cookies
        :return: Обработанный словарь cookies
        """
        if not cookies:
            cookies = self.account.data.cookies.copy()

        for exclude_cookie in exclude_cookies:
            logger.debug(f"⏭️ Исключение cookie: {exclude_cookie}")
            cookies.pop(exclude_cookie, None)

        if allowed_cookies:
            cookies = {
                k: v for k, v in cookies.items() if k in allowed_cookies
            }

        return cookies

    async def _check_response_status(
        self,
        response: ClientResponse,
        check_session_on_401: bool = True,
        raise_err_on_401: bool = True,
        retry_on_403: bool = True,
    ) -> None | NoReturn:
        """
        Проверяет статус ответа и обрабатывает ошибки.

        :param response: Ответ от сервера
        :param check_session_on_401: Проверять сессию при 401 статусе
        :param raise_err_on_401: Выбрасывать исключение при 401 статусе
        :param retry_on_403: Повторять запрос при 403 статусе
        :raises NeedCheckSession: При 401 статусе и check_session_on_401=True
        :raises MegafonAPIError: При ошибочных статусах
        :raises ClientError: При 403 статусе для повторной попытки
        """
        status = response.status
        logger.debug(f"📊 Статус ответа: {status}")

        match status:
            case 200:
                logger.debug("✅ Запрос выполнен успешно")
            case 401:
                if check_session_on_401:
                    logger.warning("⚠️ Получен 401 статус - требуется проверка сессии")
                    raise NeedCheckSession
                if raise_err_on_401:
                    logger.error(f"❌ Получен 401 статус - {response.url}")
                    raise MegafonAPIError(
                        f"Получен 401 статус - {response.url}"
                    )
                logger.debug("⏭️ Получен 401 статус (проигнорирован)")
            case 403:
                logger.warning("⚠️ Получен 403 статус - повторная попытка")
                raise ClientError(
                    "Повторная попытка отправки запроса из за 403 статуса"
                )
            case other:
                logger.error(f"❌ Плохой статус ответа: {other} - {response.method} {response.url}")
                raise MegafonAPIError(
                    f"Получен плохой статус ответа: {other}. {response.method} {response.url}"
                )

    @retrier()
    async def make_request(
        self,
        method: str,
        url: str,
        headers: dict = {},
        cookies: dict = {},
        use_strict_headers: bool = False,
        delay: float | int = DEFAULT_DELAY,
        check_session_on_401: bool = True,
        auto_update_cookies: bool = True,
        raise_err_on_401: bool = True,
        exclude_cookies: list[str] = [],
        allowed_cookies: list[str] = [],
        **request_kwargs,
    ) -> NoReturn | Response:
        """
        Выполняет HTTP-запрос к API Мегафон.

        :param method: HTTP-метод (GET, POST и т.д.)
        :param url: URL для запроса
        :param headers: Дополнительные заголовки
        :param cookies: Cookies для запроса
        :param use_strict_headers: Использовать только переданные заголовки
        :param delay: Задержка перед запросом
        :param check_session_on_401: Проверять сессию при 401 статусе
        :param auto_update_cookies: Автоматически обновлять cookies аккаунта
        :param raise_err_on_401: Выбрасывать исключение при 401 статусе
        :param exclude_cookies: Список cookies для исключения
        :param allowed_cookies: Список разрешенных cookies
        :param request_kwargs: Дополнительные параметры для aiohttp
        :return: Объект Response с результатом запроса
        :raises MegafonAPIError: При ошибочных статусах ответа
        :raises NeedCheckSession: При необходимости проверки сессии
        """
        if USE_DELAY:
            await asyncio.sleep(delay) 
        timeout = ClientTimeout(total=5)

        full_headers = self._prepare_headers(headers, use_strict_headers)
        full_cookies = self._proccess_cookies(
            cookies, exclude_cookies, allowed_cookies
        )

        logger.info(f"🌐 {method} запрос: {url}")
        logger.debug(f"🍪 Используется {len(full_cookies)} cookies")

        async with ClientSession() as session:
            async with session.request(
                method=method,
                url=url,
                headers=full_headers,
                cookies=full_cookies,
                proxy=self.account.data.proxies,
                timeout=timeout,
                **request_kwargs,
            ) as response:
                await self._check_response_status(
                    response,
                    check_session_on_401,
                    raise_err_on_401,
                )

                response = await Response.init(response)

                if auto_update_cookies:
                    await self.account.update_cookies(response.new_cookies)

                logger.info(f"✅ Запрос выполнен успешно")
                return response
