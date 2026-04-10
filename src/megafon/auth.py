"""
Модуль аутентификации для работы с API Мегафон.

Содержит класс MegafonAuthAPI для выполнения операций аутентификации,
включая проверку сессии, обновление токенов, отправку и проверку OTP-кодов.
"""

from typing import NoReturn
from uuid import uuid4

from loguru import logger

from src.megafon.config import (
    BASE_AUTH_HEADERS,
    BASE_HEADERS,
    DEFAULT_DELAY,
)
from src.megafon.datatypes import Response
from src.megafon.enums import AllowedCookies
from src.megafon.exceptions import (
    IncorrectOTPCode,
    MegafonAPIError,
    MegafonAuthAPIError,
    NeedAuthError,
    RefreshTokenUpdateFailed,
)
from src.megafon.http_client import MegafonHTTPClient

from .account import MegafonAccount


class MegafonAuthAPI(MegafonHTTPClient):
    """
    API для аутентификации в системе Мегафон.

    Предоставляет методы для управления сессией, обновления токенов,
    работы с OTP-кодами и PIN-кодами.
    """

    def __init__(self, account: MegafonAccount) -> None:
        """
        Инициализация API аутентификации.

        :param account: Аккаунт Мегафон для аутентификации
        """
        super().__init__(account)

    async def _check_authorization_need(
        self, response: Response
    ) -> None | NoReturn:
        """
        Проверяет необходимость повторной авторизации.

        :param response: Ответ от API
        :raises NeedAuthError: Если требуется повторная авторизация
        """
        if not response.json.get("authenticated", False):
            logger.warning("⚠️ Требуется повторная авторизация")
            raise NeedAuthError

    async def check_session(self, delay: int = DEFAULT_DELAY):
        """
        Проверяет и обновляет текущую сессию.

        :param delay: Задержка перед запросом
        :raises MegafonAPIError: Если не удалось обновить сессию
        """
        logger.info("🔄 Проверка и обновление сессии")
        headers = {
            "X-Cabinet-Authorization": self.account.data.access_token,
        }

        try:
            response = await self.make_request(
                "GET",
                "https://api.megafon.ru/mlk/api/auth/sessionCheck",
                delay=delay,
                headers=BASE_HEADERS | headers,
                use_strict_headers=True,
                allowed_cookies=AllowedCookies.CHECK_SESSION.value,
            )
        except MegafonAPIError as err:
            logger.error(f"❌ Не удалось обновить сессию: {err}")
            raise MegafonAPIError(f"Не удалось обновить сессию из за {err}")

        try:
            await self._check_authorization_need(response)
            await self.account.update_access_token(response)
        except NeedAuthError:
            logger.info("🔐 Требуется обновление токенов")
            await self.update_tokens()

        logger.info("✅ Сессия успешно обновлена")

    async def refresh_token(self) -> NoReturn | None:
        """
        Обновляет refresh token аккаунта.

        :raises RefreshTokenUpdateFailed: Если не удалось обновить токен
        """
        logger.info("🔄 Обновление refresh token")
        logger.debug(
            f"🔑 Используется токен: ...{self.account.data.refresh_token[-5:]}"
        )

        headers = {
            "Authorization": self.account.data.access_token,
            "X-Cabinet-Request-Id": str(uuid4()),
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        }

        data = {
            "login": self.account.data.number,
            "refreshToken": self.account.data.refresh_token,
        }
        response = await self.make_request(
            "POST",
            "https://api.megafon.ru/mlk/api/auth/refresh/login",
            headers=BASE_AUTH_HEADERS | headers,
            check_session_on_401=False,
            raise_err_on_401=False,
            use_strict_headers=True,
            allowed_cookies=AllowedCookies.REFRESH_TOKEN.value,
            data=data,
        )
        if response.status != 200:
            logger.error(
                f"❌ Не удалось обновить refresh token (статус {response.status})"
            )
            raise RefreshTokenUpdateFailed

        await self.account.update_tokens(response)
        logger.info("✅ Refresh token успешно обновлен")

    async def push_pin(self):
        """
        Отправляет PIN-код для аутентификации.

        :raises MegafonAPIError: Если не удалось отправить PIN-код
        """
        logger.info("🔐 Отправка PIN-кода для аутентификации")
        headers = {
            "Authorization": self.account.data.access_token,
            "X-Cabinet-Request-Id": str(uuid4()),
            "Content-Type": "application/json",
        }
        json_data = {
            "pin": self.account.data.pin,
            "msisdn": self.account.data.number,
        }

        response = await self.make_request(
            "POST",
            "https://api.megafon.ru/mlk/api/auth/pin",
            json=json_data,
            headers=BASE_AUTH_HEADERS | headers,
            use_strict_headers=True,
            check_session_on_401=False,
            allowed_cookies=AllowedCookies.PUSH_PIN.value,
        )

        if response.status != 200:
            logger.error(
                f"❌ Не удалось отправить PIN-код (статус {response.status})"
            )
            raise MegafonAPIError(
                f"Не удалось отправить биометрию из за плохого статуса. Response: {response.json}"
            )

        await self._check_authorization_need(response)
        await self.account.update_tokens(response)
        logger.info("✅ PIN-код успешно отправлен")

    async def update_tokens(self) -> None | NoReturn:
        """
        Обновляет access и refresh токены аккаунта.

        Сначала пытается обновить через refresh token,
        при неудаче использует PIN-код.
        """
        logger.info("🔐 Начало обновления токенов")
        try:
            await self.refresh_token()
        except RefreshTokenUpdateFailed:
            logger.warning(
                "⚠️ Обновление через refresh token не удалось, используем PIN-код"
            )
            await self.push_pin()

        await self.check_session()
        logger.info("✅ Токены успешно обновлены")

    async def send_otp(self) -> None | NoReturn:
        """
        Отправляет OTP-код на номер телефона.

        :raises MegafonAPIError: Если не удалось отправить код или нужно подождать
        """
        logger.info(
            f"📱 Отправка OTP-кода на номер {self.account.data.number}"
        )
        timeout = await self.get_send_otp_timeout()
        if timeout:
            logger.warning(
                f"⏳ Нужно подождать {timeout} секунд перед отправкой нового кода"
            )
            raise MegafonAPIError(
                f"Нужно подождать {timeout} секунд перед отправкой нового кода"
            )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        }
        data = {
            "captchaReady": "true",
            "login": self.account.data.number,
        }
        response = await self.make_request(
            "POST",
            "https://api.megafon.ru/mlk/api/auth/otp/request",
            headers=BASE_AUTH_HEADERS | headers,
            use_strict_headers=True,
            check_session_on_401=False,
            data=data,
        )

        data = response.json
        if not data.get("ok", False):
            logger.error("❌ Не удалось отправить OTP-код")
            raise MegafonAPIError("Не удалось отправить код для входа")

        logger.info("✅ OTP-код успешно отправлен")

    async def submit_otp(self, otp_code: str) -> None | NoReturn:
        """
        Проверяет введенный OTP-код.

        :param otp_code: OTP-код для проверки
        :raises IncorrectOTPCode: Если код неверный
        """
        logger.info("🔐 Проверка OTP-кода")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        }
        data = {
            "login": self.account.data.number,
            "otp": otp_code,
        }

        try:
            response = await self.make_request(
                "POST",
                "https://api.megafon.ru/mlk/api/auth/otp/submit",
                headers=BASE_AUTH_HEADERS | headers,
                data=data,
                use_strict_headers=True,
                check_session_on_401=False,
            )
        except MegafonAPIError:
            logger.error("❌ Неверный OTP-код")
            raise IncorrectOTPCode("Дан неверный OTP код")

        data = response.json
        await self._check_authorization_need(response)
        await self.account.update_tokens(response)
        logger.info("✅ OTP-код принят, аутентификация успешна")

    async def get_send_otp_timeout(self) -> int | NoReturn:
        """
        Получает время ожидания перед повторной отправкой OTP.

        :return: Количество секунд до возможности повторной отправки
        """
        logger.debug("⏱️ Получение таймаута отправки OTP")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        }

        params = {
            "login": self.account.data.number,
            "verificationMethod": "AUTH_OTP",
        }

        response = await self.make_request(
            "GET",
            "https://api.megafon.ru/mlk/api/otp/currentTimeout",
            params=params,
            headers=BASE_AUTH_HEADERS | headers,
            use_strict_headers=True,
            check_session_on_401=False,
        )

        data = response.json
        timeout = data.get("timeout", 0)
        logger.debug(f"⏱️ Таймаут: {timeout} секунд")
        return timeout

    async def setup_pin(self) -> NoReturn | None:
        """
        Устанавливает PIN-код для аккаунта.

        :raises MegafonAuthAPIError: Если не удалось установить PIN-код
        """
        logger.info("🔐 Установка PIN-кода")
        headers = {
            "Authorization": self.account.data.access_token,
            "X-Cabinet-Request-Id": str(uuid4()),
            "Content-Type": "application/json",
        }

        json_data = {
            "pin": self.account.data.pin,
        }

        try:
            await self.make_request(
                "POST",
                "https://api.megafon.ru/mlk/api/profile/pin",
                headers=BASE_AUTH_HEADERS | headers,
                json=json_data,
                check_session_on_401=False,
                use_strict_headers=True,
            )
            logger.info("✅ PIN-код успешно установлен")
        except MegafonAPIError as err:
            logger.error(f"❌ Не удалось установить PIN-код: {err}")
            raise MegafonAuthAPIError(f"Не удалось установить пин-код: {err}")
