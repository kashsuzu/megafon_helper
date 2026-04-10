"""
Модуль для управления аккаунтами Мегафон.

Содержит класс MegafonAccount для работы с данными аккаунта,
включая управление токенами, cookies и сохранение в базу данных.
"""

from typing import NoReturn

from loguru import logger

from src.database import Database

from .datatypes import MegafonAccountData, Response
from .exceptions import MegafonAPIError


class MegafonAccount:
    """
    Класс для управления аккаунтом Мегафон.

    Предоставляет методы для обновления токенов, cookies и
    сохранения данных аккаунта в базу данных.
    """

    def __init__(self, account_data: MegafonAccountData) -> None:
        """
        Инициализация аккаунта Мегафон.

        :param account_data: Данные аккаунта
        """
        self.data = account_data
        self.database = Database()

    async def save_account_data_to_db(self, save_data: bool = True):
        """
        Сохраняет данные аккаунта в базу данных.

        :param save_data: Флаг, определяющий нужно ли сохранять данные
        """
        if save_data:
            logger.info(
                f"💾 Сохранение данных аккаунта #{self.data.account_id}"
            )
            await self.database.update_account_data(self.data)

    async def update_access_token(
        self, response: Response, save_data: bool = True
    ) -> None | NoReturn:
        """
        Обновляет access token из ответа API.

        :param response: Ответ от API с новым токеном
        :param save_data: Флаг сохранения данных в БД
        :raises MegafonAPIError: Если токен не найден в ответе
        """
        logger.info("🔑 Обновление access token")
        data = response.json

        if not (new_access_token := data.get("jwtToken", "")):
            logger.error("❌ JWT token не найден в ответе")
            raise MegafonAPIError(
                f"Не удалось найти jwt token при обновлении resfresh token\n{data}"
            )
        if new_access_token == self.data.access_token:
            logger.debug("⏭️ Access token не изменился, пропускаю обновление")
            return

        logger.debug(f"✅ Access token обновлен: ...{new_access_token[-5:]}")
        self.data.access_token = f"Bearer {new_access_token}"
        await self.save_account_data_to_db(save_data)

    async def update_refresh_token(
        self, response: Response, save_data: bool = True
    ) -> NoReturn | None:
        """
        Обновляет refresh token из cookies ответа API.

        :param response: Ответ от API с новыми cookies
        :param save_data: Флаг сохранения данных в БД
        :raises MegafonAPIError: Если refresh token не найден или невалиден
        """
        logger.info("🔄 Обновление refresh token")
        new_refresh_token = response.new_cookies.get(
            "X-Cabinet-Refresh-Token", ""
        )
        if not new_refresh_token:
            logger.error("❌ Refresh token не найден или невалиден")
            raise MegafonAPIError("Найден невалидный refresh токен")

        logger.debug(f"✅ Refresh token обновлен: ...{new_refresh_token[-5:]}")
        self.data.refresh_token = new_refresh_token
        await self.save_account_data_to_db(save_data)

    async def update_tokens(self, response: Response) -> None | NoReturn:
        """
        Обновляет оба токена (access и refresh) из ответа API.

        :param response: Ответ от API с новыми токенами
        :raises MegafonAPIError: Если токены не найдены или невалидны
        """
        logger.info("🔐 Обновление токенов (access + refresh)")
        await self.update_access_token(response, save_data=False)
        await self.update_refresh_token(response, save_data=False)
        await self.save_account_data_to_db()
        logger.info("✅ Токены успешно обновлены")

    async def update_cookies(
        self,
        new_cookies: dict,
        exclude_cookies: list[str] = [],
        save_data: bool = True,
    ):
        """
        Обновляет cookies аккаунта.

        :param new_cookies: Словарь с новыми cookies
        :param exclude_cookies: Список cookies, которые нужно исключить
        :param save_data: Флаг сохранения данных в БД
        """
        if not new_cookies:
            return

        logger.info(f"🍪 Обновление cookies (получено {len(new_cookies)} шт.)")
        updated_count = 0
        for k, v in new_cookies.items():
            if k in exclude_cookies:
                logger.debug(f"⏭️ Исключение cookie: {k}")
                continue
            logger.debug(f"✅ Обновление cookie: {k}")
            self.data.cookies[k] = v
            updated_count += 1

        logger.info(f"✅ Обновлено {updated_count} cookies")
        await self.save_account_data_to_db(save_data)

    async def delete(self) -> None:
        """
        Удаляет аккаунт из базы данных.
        """
        logger.info(f"🗑️ Удаление аккаунта #{self.data.account_id}")
        await self.database.delete_account(self.data.account_id)

    # @classmethod
    # def create(cls, number: str) -> Self:
    #     logger.info("Создание нового аккаунта")
    #     account_id = str(cls._get_accounts_amount() + 1)

    #     account = cls(account_id=account_id, number=number)
    #     account._write_data()
    #     return account

    # def delete(self):
    #     "raises OSErorr если не удалось удалить"
    #     file_name = f"{self.account_id}.json"
    #     os.remove(os.path.join(ACCOUNTS_PATH, file_name))

    # @staticmethod
    # def _get_accounts_amount() -> int:
    #     return len(os.listdir(ACCOUNTS_PATH))

    # def _write_data(self, write_data: bool = True):
    #     file_name = f"{self.account_id}.json"
    #     if not write_data:
    #         return
    #     logger.info(f"Обновление информации об аккаунте {self.account_id}")
    #     path = os.path.join(
    #         ACCOUNTS_PATH,
    #         file_name,
    #     )
    #     with open(path, "w") as file:
    #         json.dump(self.__dict__, file, indent=4)

    # def update_jwt(self, response, write_data: bool = True) -> None | NoReturn:
    #     self.update_access_token(response)
    #     self.update_refresh_token(response)
    #     self._write_data(write_data)
