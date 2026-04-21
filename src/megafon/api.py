"""
Модуль API для работы с дополнительными номерами Мегафон.

Содержит класс MegafonAPI для управления дополнительными номерами,
включая проверку доступности, подключение, отключение и получение информации.
"""

from typing import NoReturn

from loguru import logger

from src.megafon.auth import MegafonAuthAPI
from src.megafon.config import DEFAULT_DELAY, ONE_NUMBER_PRICE
from src.megafon.datatypes import (
    NumberInfo,
    ServiceAvailabilityInfo,
)
from src.megafon.exceptions import MegafonAPIError, ServiceAvailabilityError
from src.megafon.http_client import NeedCheckSession

from .account import MegafonAccount


def session_checker(func):
    """
    Декоратор для автоматической проверки сессии при ошибках.

    При возникновении NeedCheckSession автоматически обновляет сессию
    и повторяет запрос.

    :param func: Декорируемая функция
    :return: Обернутая функция с проверкой сессии
    """

    async def wrapper(self: MegafonAPI, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except NeedCheckSession:
            await self.check_session()
            return await func(self, *args, **kwargs)

    return wrapper


class MegafonAPI(MegafonAuthAPI):
    """
    API для работы с дополнительными номерами Мегафон.

    Предоставляет методы для управления дополнительными номерами,
    включая подключение, отключение, проверку доступности и получение баланса.
    """

    def __init__(self, account: MegafonAccount) -> None:
        """
        Инициализация API дополнительных номеров.

        :param account: Аккаунт Мегафон
        """
        super().__init__(account)

    @session_checker
    async def check_service_availability(
        self, delay: int = DEFAULT_DELAY
    ) -> ServiceAvailabilityInfo:
        """
        Проверяет доступность сервиса дополнительных номеров.

        :param delay: Задержка перед запросом
        :return: Информация о доступности сервиса
        """
        logger.info("🔍 Проверка доступности сервиса дополнительных номеров")
        response = await self.make_request(
            "GET",
            "https://api.megafon.ru/mlk/api/additionalNumbers/availableTypes?hasAdditionalNumber=false",
            delay=delay,
        )
        data = response.json
        available = data.get("success", False)
        message = data.get("conflicts", [{}])[0].get("conflictMessage", "")

        if available:
            logger.info("✅ Сервис доступен")
        else:
            logger.warning(f"⚠️ Сервис недоступен: {message}")

        return ServiceAvailabilityInfo(available=available, message=message)

    @session_checker
    async def get_available_numbers(
        self, delay: int = DEFAULT_DELAY
    ) -> list[NumberInfo]:
        """
        Получает список доступных для подключения номеров.

        :param delay: Задержка перед запросом
        :return: Список доступных номеров
        :raises MegafonAPIError: Если нет доступных номеров
        """
        logger.info("📋 Получение списка доступных номеров")
        response = await self.make_request(
            "GET",
            "https://api.megafon.ru/mlk/api/additionalNumbers/availableForAdd?types=FEDERAL",
            delay=delay,
        )
        data = response.json
        numbers_info = data.get("availableForAdd", [{}])[0].get(
            "numbersInfo", []
        )

        if not numbers_info:
            logger.error("❌ Нет доступных номеров для подключения")
            raise MegafonAPIError("Нет доступных номеров для подключения")

        numbers = [
            NumberInfo(
                str(number_info.get("number")),
                str(number_info.get("id")),
            )
            for number_info in numbers_info
        ]

        logger.info(f"✅ Найдено {len(numbers)} доступных номеров")
        return numbers

    @session_checker
    async def take_number(
        self, number_info: NumberInfo, delay: int = DEFAULT_DELAY
    ) -> NoReturn | None:
        """
        Подключает дополнительный номер к аккаунту.

        :param number_info: Информация о номере для подключения
        :param delay: Задержка перед запросом
        :raises MegafonAPIError: Если не удалось подключить номер
        """
        logger.info(f"📞 Подключение номера {number_info.number}")
        headers = {
            "X-Csrf-Token": self.account.data.cookies.get("NEW-CSRF-TOKEN")
        }

        try:
            await self.make_request(
                "POST",
                f"https://api.megafon.ru/mlk/api/additionalNumbers/{number_info.number_id}",
                headers=headers,
                delay=delay,
            )
            logger.info(f"✅ Номер {number_info.number} успешно подключен")
        except MegafonAPIError as err:
            logger.error(
                f"❌ Не удалось подключить номер {number_info.number}: {err}"
            )
            raise MegafonAPIError(
                f"Не удалось подключить номер {number_info} из за {err}"
            )

    @session_checker
    async def delete_number(
        self, number_info: NumberInfo, delay: int = DEFAULT_DELAY
    ) -> NoReturn | None:
        """
        Отключает дополнительный номер от аккаунта.

        :param number_info: Информация о номере для отключения
        :param delay: Задержка перед запросом
        :raises MegafonAPIError: Если не удалось отключить номер
        """
        logger.info(f"📵 Отключение номера {number_info.number}")
        headers = {
            "X-Csrf-Token": self.account.data.cookies.get("NEW-CSRF-TOKEN", "")
        }
        try:
            await self.make_request(
                "DELETE",
                f"https://api.megafon.ru/mlk/api/additionalNumbers/{number_info.number_id}",
                headers=headers,
                delay=delay,
            )
            logger.info(f"✅ Номер {number_info.number} успешно отключен")
        except MegafonAPIError as err:
            logger.error(
                f"❌ Не удалось отключить номер {number_info.number}: {err}"
            )
            raise MegafonAPIError(
                f"Не удалось отключить номер {number_info} из за {err}"
            )

    @session_checker
    async def get_activated_numbers(
        self, delay: int = DEFAULT_DELAY
    ) -> NoReturn | list[NumberInfo]:
        """
        Получает список подключенных дополнительных номеров.

        :param delay: Задержка перед запросом
        :return: Список подключенных номеров
        :raises MegafonAPIError: Если получен некорректный ответ
        """
        logger.info("📋 Получение списка подключенных номеров")
        response = await self.make_request(
            "GET",
            "https://api.megafon.ru/mlk/api/additionalNumbers/list",
            delay=delay,
        )
        data = response.json
        try:
            if not data.get("hasAdditionalNumbers", True):
                logger.info("ℹ️ Подключенных номеров нет")
                return []
        except Exception:
            logger.error("❌ Получен некорректный ответ от API")
            raise MegafonAPIError(
                f"Получен некорректный ответ при попытке получения списка активных номеров\n{data}"
            )

        activated_numbers = [
            NumberInfo(number_info.get("number"), number_info.get("id"))
            for number_info in data.get("additionalNumbersList", [])
        ]

        logger.info(
            f"✅ Найдено {len(activated_numbers)} подключенных номеров"
        )
        return activated_numbers

    @session_checker
    async def get_balance(self, delay: int = DEFAULT_DELAY) -> str | NoReturn:
        """
        Получает текущий баланс аккаунта.

        :param delay: Задержка перед запросом
        :return: Баланс в виде строки
        """
        logger.info("💰 Получение баланса аккаунта")
        response = await self.make_request(
            "GET",
            "https://api.megafon.ru/mlk/api/main/balance",
            delay=delay,
        )
        data = response.json
        balance = str(int(data.get("balance", "0")))
        logger.info(f"✅ Баланс: {balance} ₽")
        return balance

    async def activate_numbers(self) -> list[str] | NoReturn:
        """
        Подключает максимально возможное количество дополнительных номеров.

        Проверяет доступность сервиса, баланс и подключает номера
        до достижения лимита (3 номера).

        :return: Список подключенных номеров
        :raises ServiceAvailabilityError: Если сервис недоступен
        :raises MegafonAPIError: При ошибках подключения или недостатке средств
        """
        logger.info("🚀 Начало подключения дополнительных номеров")
        activated_numbers = []
        max_attempts = 5
        attempt = 0

        service_avaibility = await self.check_service_availability()
        if not service_avaibility.available:
            logger.error(f"❌ Сервис недоступен: {service_avaibility.message}")
            raise ServiceAvailabilityError(
                f"Сервис недоступен по причине: {service_avaibility.message}"
            )

        activated_numbers_amount = len(await self.get_activated_numbers())
        available_for_activation_amount = 3 - activated_numbers_amount
        logger.info(
            f"📊 Можно подключить еще {available_for_activation_amount} номеров"
        )

        balance = await self.get_balance()
        required_balance = available_for_activation_amount * ONE_NUMBER_PRICE
        if int(balance) < required_balance:
            logger.error(
                f"❌ Недостаточно средств: требуется {required_balance} ₽, доступно {balance} ₽"
            )
            raise MegafonAPIError(
                f"Недостаточно средств: требуется {required_balance} ₽, доступно {balance} ₽"
            )

        while len(activated_numbers) != available_for_activation_amount:
            attempt += 1
            logger.info(f"🔄 Попытка {attempt}/{max_attempts}")

            if max_attempts == attempt:
                logger.error("❌ Достигнуто максимальное количество попыток")
                raise MegafonAPIError(
                    "Не удалось активировать номера. Достигнуто максимальное количество попыток"
                )

            try:
                available_numbers = await self.get_available_numbers()
                number_info = available_numbers[-1]
            except MegafonAPIError as err:
                logger.error(f"❌ Не удалось получить доступные номера: {err}")
                raise MegafonAPIError(
                    f"Не удалось получить доступные номера из за {err}"
                )

            try:
                await self.take_number(number_info)
                activated_numbers.append(number_info.number)
            except MegafonAPIError as err:
                logger.warning(
                    f"⚠️ Не удалось подключить номер {number_info.number}: {err}"
                )

        logger.info(f"✅ Успешно подключено {len(activated_numbers)} номеров")
        return activated_numbers

    async def delete_all_numbers(self) -> int:
        """
        Отключает все подключенные дополнительные номера.

        Получает список активных номеров и отключает каждый из них.
        Продолжает работу даже при ошибках отключения отдельных номеров.
        :raises MegafonAPIError: Если не удалось получить список номеров или отключить один из них
        """
        deleted_numbers_amount = 0
        logger.info("🗑️ Начало отключения всех номеров")
        try:
            activated_numbers = await self.get_activated_numbers()
            if not activated_numbers:
                logger.info("ℹ️ Нет номеров для отключения")
                return deleted_numbers_amount

            logger.info(
                f"📋 Найдено {len(activated_numbers)} номеров для отключения"
            )
        except MegafonAPIError as err:
            logger.error(f"❌ Ошибка при получении списка номеров: {err}")
            raise MegafonAPIError(
                f"Не удалось получить список номеров из за {err}"
            )

        for number_info in activated_numbers:
            try:
                await self.delete_number(number_info, delay=2)
                deleted_numbers_amount+=1
            except MegafonAPIError as err:
                logger.error(
                    f"❌ Не удалось отключить номер {number_info.number}: {err}"
                )
                raise MegafonAPIError(
                    f"Не удалось отключить номер {number_info.number} из за {err}"
                )

        logger.info(f"✅ Процесс отключения номеров завершен(отключено {deleted_numbers_amount} номеров)")
        return deleted_numbers_amount
