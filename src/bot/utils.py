import asyncio
import re
from typing import NoReturn

import aiohttp
import phonenumbers
from loguru import logger

from src.megafon.http_client import retrier


def proxy_format_is_valid(raw: str) -> bool:
    """Returns False if proxy format is incorrect"""
    pattern_with_auth = r"^[^:@\s]+:[^:@\s]+@[^:@\s]+:\d{1,5}$"
    pattern_no_auth = r"^[^:@\s]+:\d{1,5}$"

    if not (
        re.fullmatch(pattern_with_auth, raw)
        or re.fullmatch(pattern_no_auth, raw)
    ):
        return False

    return True


@retrier()
async def check_proxy_availability(proxy: str) -> None | NoReturn:
    """
    Проверяет, что прокси живой и по нему можно сделать HTTP-запрос.
    Если прокси сервер или сервис ipify не доступны, то выдаст ошибку.

    """

    timeout = aiohttp.ClientTimeout(total=5)
    logger.debug(f"Proxy={proxy}")
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                "https://api.ipify.org",
                proxy=proxy,
            ) as response:
                response.raise_for_status()
                text = await response.text()

                logger.debug(f"Прокси {proxy} доступен, внешний IP: {text}")

    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        logger.error(f"Прокси {proxy} недоступен: {err}")
        raise err


def format_phone_number(number: str) -> str:
    try:
        phone_number = phonenumbers.parse(number, "RU")
        return phonenumbers.format_number(
            phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )
    except Exception:
        return number
