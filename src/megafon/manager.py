"""
Модуль менеджера для работы с API Мегафон.

Содержит класс MegafonManager - высокоуровневый интерфейс для управления
аккаунтом Мегафон, объединяющий функциональность API и аутентификации.
"""
from src.megafon.account import MegafonAccount

from .api import MegafonAPI


class MegafonManager(MegafonAPI):
    """
    Менеджер для управления аккаунтом Мегафон.

    Высокоуровневый класс, объединяющий все возможности работы с API Мегафон:
    аутентификацию, управление сессией и работу с дополнительными номерами.
    Наследует функциональность от MegafonAPI, который в свою очередь
    наследует от MegafonAuthAPI и MegafonHTTPClient.
    """

    def __init__(self, account: MegafonAccount) -> None:
        """
        Инициализация менеджера Мегафон.

        :param account: Аккаунт Мегафон для управления
        """
        super().__init__(account)
