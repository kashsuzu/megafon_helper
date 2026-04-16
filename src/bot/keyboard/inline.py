from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.filters.callback_data import (  # noqa: F401
    AccountsCallbackData,
    AddAccountCallbackData,
    MenuCallbackData,
)
from src.megafon.manager import MegafonManager


class InlineKeyboard:
    def __init__(self, megafon_managers: list[MegafonManager]) -> None:
        self.megafon_managers = megafon_managers
        self.max_page = (len(self.megafon_managers) + 3) // 4

    def remove_megafon_managers_by_account_id(self, account_id: int):
        for megafon_manager in self.megafon_managers:
            if megafon_manager.account.data.account_id == account_id:
                self.megafon_managers.remove(megafon_manager)
                break

    def get_megafon_managers_on_page(self, page: int) -> list[MegafonManager]:
        return self.megafon_managers[(page - 1) * 4 : page * 4]

    def menu(self, page: int = 1) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        megafon_managers = self.get_megafon_managers_on_page(page)

        builder.button(
            text="Добавить аккаунт",
            callback_data=MenuCallbackData(action="add_account").pack(),
        )
        builder.attach(InlineKeyboardBuilder.from_markup(self.accounts(page)))

        builder.button(
            text="Подключить везде",
            style="success",
            callback_data=AccountsCallbackData(
                action="activate_on_all_accounts",
                page=page,
                max_page=self.max_page,
            ).pack(),
        )
        builder.button(
            text="Отключить везде",
            style="danger",
            callback_data=AccountsCallbackData(
                action="deactivate_on_all_accounts",
                page=page,
                max_page=self.max_page,
            ).pack(),
        )
        megafon_accounts_colum_size = (
            [1] * len(megafon_managers) if megafon_managers else []
        )
        builder.adjust(1, *megafon_accounts_colum_size, 4, 1, 1)
        return builder.as_markup()

    @property
    def cancel(
        self,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=MenuCallbackData(action="back_to_main_menu").pack(),
        )
        builder.adjust(1)
        return builder.as_markup()

    @property
    def skip_enter_label(self):
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Пропустить",
            style="primary",
            callback_data=AddAccountCallbackData(action="skip_enter_label").pack(),
        )
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=MenuCallbackData(action="back_to_main_menu").pack(),
        )
        builder.adjust(1)
        return builder.as_markup()


    def cancel_change_proxy(self, account_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=AccountsCallbackData(
                action="show_info", account_id=account_id
            ).pack(),
        )
        builder.adjust(1)
        return builder.as_markup()

    def cancel_change_label(self, account_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=AccountsCallbackData(
                action="show_info", account_id=account_id
            ).pack(),
        )
        builder.adjust(1)
        return builder.as_markup()

    def confirm_change_proxy(self, account_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Подтвердить",
            style="success",
            callback_data=AccountsCallbackData(
                action="confirm_proxy", account_id=account_id
            ).pack(),
        )
        builder.button(
            text="Изменить",
            style="primary",
            callback_data=AccountsCallbackData(
                action="change_new_proxy",
                account_id=account_id,
            ).pack(),
        )
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=AccountsCallbackData(
                action="show_info", account_id=account_id
            ).pack(),
        )
        builder.adjust(1)
        return builder.as_markup()

    @property
    def otp(
        self,
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Отправить повторно",
            style="primary",
            callback_data=AddAccountCallbackData(action="resend_otp").pack(),
        )
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=MenuCallbackData(action="back_to_main_menu").pack(),
        )
        builder.adjust(1)
        return builder.as_markup()

    @property
    def confirm_proxy(self) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Подтвердить",
            style="success",
            callback_data=AddAccountCallbackData(
                action="confirm_proxy"
            ).pack(),
        )
        builder.button(
            text="Изменить",
            style="primary",
            callback_data=AddAccountCallbackData(action="change_proxy").pack(),
        )
        builder.button(
            text="Отмена",
            style="danger",
            callback_data=MenuCallbackData(action="back_to_main_menu").pack(),
        )
        builder.adjust(1)
        return builder.as_markup()

    def account_actions(
        self, account_id: int, page: int = 1
    ) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        builder.button(
            text="Подключить",
            style="success",
            callback_data=AccountsCallbackData(
                action="activate", account_id=account_id
            ).pack(),
        )
        builder.button(
            text="Отключить",
            style="danger",
            callback_data=AccountsCallbackData(
                action="deactivate", account_id=account_id
            ).pack(),
        )
        builder.button(
            text="Удалить",
            callback_data=AccountsCallbackData(
                action="delete", account_id=account_id
            ).pack(),
        )
        builder.button(
            text="Обновить",
            callback_data=AccountsCallbackData(
                action="show_info", account_id=account_id
            ).pack(),
        )

        builder.button(
            text="Изменить прокси",
            callback_data=AccountsCallbackData(
                action="change_proxy", account_id=account_id
            ).pack(),
        )
        builder.button(
            text="Изменить метку",
            callback_data=AccountsCallbackData(
                action="change_label", account_id=account_id
            ).pack(),
        )
        builder.button(
            text="Назад",
            callback_data=MenuCallbackData(
                action="back_to_main_menu", page=page
            ).pack(),
        )
        builder.adjust(2)
        return builder.as_markup()

    def accounts(self, page: int = 1) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()

        megafon_managers = self.get_megafon_managers_on_page(page)

        for megafon_manager in megafon_managers:
            phone_number, account_id = (
                megafon_manager.account.data.formated_number,
                megafon_manager.account.data.account_id,
            )
            builder.add(
                InlineKeyboardButton(
                    text=f"#{account_id} | " + f"{phone_number}",
                    style="primary",
                    callback_data=AccountsCallbackData(
                        action="show_info",
                        account_id=megafon_manager.account.data.account_id,
                    ).pack(),
                )
            )

        builder.row(
            InlineKeyboardButton(
                text="<<",
                callback_data=AccountsCallbackData(
                    action="prev_page",
                    page=1,
                    max_page=self.max_page,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="←",
                callback_data=AccountsCallbackData(
                    action="prev_page", page=page - 1, max_page=self.max_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text="→",
                callback_data=AccountsCallbackData(
                    action="next_page", page=page + 1, max_page=self.max_page
                ).pack(),
            ),
            InlineKeyboardButton(
                text=">>",
                callback_data=AccountsCallbackData(
                    action="next_page",
                    page=self.max_page,
                    max_page=self.max_page,
                ).pack(),
            ),
            width=1,
        )

        return builder.as_markup()
