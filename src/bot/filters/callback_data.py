from aiogram.filters.callback_data import CallbackData


class MenuCallbackData(CallbackData, prefix="menu"):
    action: str
    page: int = 1


class AccountsCallbackData(CallbackData, prefix="accounts"):
    action: str
    account_id: int = 0
    page: int = 1
    max_page: int = 1


class AddAccountCallbackData(CallbackData, prefix="add_account"):
    action: str

