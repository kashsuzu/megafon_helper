"""
Модуль с типами данных для работы с API Мегафон.

Содержит классы для представления ответов API, информации о номерах,
доступности сервисов и данных аккаунта Мегафон.
"""

import datetime
import json
from dataclasses import dataclass, field
from typing import NamedTuple, NoReturn, Self

from aiohttp import ClientResponse
from loguru import logger


class ServiceAvailabilityInfo(NamedTuple):
    """
    Информация о доступности сервиса.

    :param available: Доступен ли сервис
    :param message: Сообщение о статусе доступности
    """

    available: bool
    message: str


class NumberInfo(NamedTuple):
    """
    Информация о телефонном номере.

    :param number: Телефонный номер
    :param number_id: Уникальный идентификатор номера
    """

    number: str
    number_id: str


class Response:
    """
    Обертка над ответом HTTP-запроса с дополнительной обработкой.

    Предоставляет удобный доступ к статусу, заголовкам, JSON-данным
    и новым cookies из ответа сервера.
    """

    def __init__(
        self,
        response: ClientResponse,
        json: dict,
        new_cookies: dict,
    ) -> None:
        """
        Инициализация объекта ответа.

        :param response: Объект ответа aiohttp
        :param json: Распарсенные JSON-данные из ответа
        :param new_cookies: Новые cookies из заголовков ответа
        """
        self.response = response
        self.status = response.status
        self.headers = response.headers
        self.json = json
        self.new_cookies = new_cookies

    @staticmethod
    async def get_json(response: ClientResponse) -> dict:
        """
        Извлекает и парсит JSON из ответа сервера.

        :param response: Объект ответа aiohttp
        :return: Словарь с данными JSON или пустой словарь при ошибке
        """
        json = {}
        try:
            json = await response.json()
        except Exception as err:
            logger.warning(
                f"Не удалось преобразовать ответ в json:\nErr:\n{err}\n{response.content}"
            )

        return json

    @staticmethod
    def get_new_cookies(response: ClientResponse) -> dict | NoReturn:
        """
        Извлекает новые cookies из заголовков ответа.

        :param response: Объект ответа aiohttp
        :return: Словарь с новыми cookies
        """
        logger.info("Получение новых cookies")
        cookies = {}
        set_cookie_list = response.headers.getall("Set-Cookie", [])
        for set_cookie in set_cookie_list:
            if not set_cookie:
                continue
            key, value = set_cookie.split(";")[0].strip().split("=")
            logger.debug(f"Куки: {key}={value[-10:]}")
            cookies[key] = value

        return cookies

    @classmethod
    async def init(cls, response: ClientResponse) -> Self:
        """
        Асинхронная фабрика для создания объекта Response.

        :param response: Объект ответа aiohttp
        :return: Инициализированный объект Response
        """
        logger.info("Инициализация ответа (response)")
        json = await cls.get_json(response)
        new_cookies = cls.get_new_cookies(response)

        return cls(response, json, new_cookies)  # type: ignore


@dataclass
class MegafonAccountData:
    """
    Данные аккаунта Мегафон.

    Содержит всю необходимую информацию для аутентификации и работы
    с API Мегафон, включая токены, cookies и информацию о номере.
    """

    account_id: int = 0
    owner_id: int = 0
    access_token: str = ""
    refresh_token: str = ""
    cookies: dict = field(default_factory=lambda: {})
    number: str = ""
    proxies: str = ""
    last_activate_datetime: str = datetime.datetime.now().strftime(
        "%d.%m.%Y %H:%M"
    )
    pin: str = ""
    formated_number: str = ""

    def __post_init__(self):
        """
        Пост-инициализация для десериализации cookies и даты.

        Преобразует строковые представления cookies и timestamp
        в соответствующие типы данных.
        """
        if not isinstance(self.cookies, dict):
            try:
                self.cookies = json.loads(self.cookies)
            except json.JSONDecodeError:
                logger.warning("Не удалось десериализовать cookies в dict")
                self.cookies = {}

        if not isinstance(self.last_activate_datetime, str):
            self.last_activate_datetime = datetime.datetime.fromtimestamp(
                self.last_activate_datetime
            ).strftime("%d.%m.%Y %H:%M")

    def get_data_for_db(self):
        """
        Подготавливает данные аккаунта для сохранения в базу данных.

        Сериализует cookies в JSON-строку и datetime в timestamp.

        :return: Объект MegafonAccountData с сериализованными данными
        """
        account_data = MegafonAccountData(**self.__dict__)
        account_data.cookies = json.dumps(self.cookies)  # type: ignore
        account_data.last_activate_datetime = int(
            datetime.datetime.strptime(
                self.last_activate_datetime, "%d.%m.%Y %H:%M"
            ).timestamp()
        )  # type: ignore

        return account_data
