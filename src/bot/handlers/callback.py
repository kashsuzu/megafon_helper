import asyncio
import datetime

import aiohttp
from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from src.bot.filters.callback_data import (
    AccountsCallbackData,
    AddAccountCallbackData,
    MenuCallbackData,
)
from src.bot.fsm.add_account import AddAccountStates
from src.bot.fsm.change_proxy import ChangeProxyStates, ChangeLabelStates, ChangeLabelStates
from src.bot.keyboard.inline import InlineKeyboard
from src.bot.utils import check_proxy_availability
from src.database import Database
from src.megafon.account import MegafonAccount
from src.megafon.datatypes import MegafonAccountData
from src.megafon.exceptions import MegafonAPIError, ServiceAvailabilityError
from src.megafon.manager import MegafonManager
from loguru import logger
router = Router()


@router.callback_query(
    StateFilter(AddAccountStates),
    MenuCallbackData.filter(F.action == "back_to_main_menu"),
)
async def cancel_add_account(
    callback: CallbackQuery,
    keyboard: InlineKeyboard,
    database: Database,
    state_data: dict,
    state: FSMContext,
):
    megafon_manager = state_data["megafon_manager"]
    account_id = megafon_manager.account.data.account_id
    await database.delete_account(account_id)
    keyboard.remove_megafon_managers_by_account_id(account_id)
    await callback.message.edit_text(
        html.bold("🚫 Добавление аккаунта отменено"),
        reply_markup=keyboard.menu(),
    )
    await state.clear()


@router.callback_query(
    MenuCallbackData.filter(F.action == "back_to_main_menu")
)
async def back_to_main_menu(
    callback: CallbackQuery,
    keyboard: InlineKeyboard,
    callback_data: MenuCallbackData,
):
    await callback.message.edit_text(
        html.bold("📋 Главное меню 📋"),
        reply_markup=keyboard.menu(callback_data.page),
    )


@router.callback_query(
    AddAccountCallbackData.filter(F.action == "skip_enter_label")
)
async def skip_enter_label(
    callback: CallbackQuery,
    keyboard: InlineKeyboard,
    state: FSMContext,
    state_data: dict
):
    megafon_manager: MegafonManager = state_data["megafon_manager"]
    await megafon_manager.account.save_account_data_to_db()
    keyboard.remove_megafon_managers_by_account_id(
        megafon_manager.account.data.account_id
    )
    keyboard.megafon_managers.append(megafon_manager)
    await callback.message.answer(
        html.bold("✅ Аккаунт успешно добавлен!"),
        reply_markup=keyboard.menu(),
    )
    await state.clear()


# @router.callback_query(
#     AccountsCallbackData.filter(F.action == "back_to_accounts")
# )
# async def back_to_accounts(callback: CallbackQuery, keyboard: InlineKeyboard):
#     await callback.message.edit_text(
#         html.bold("Выберите аккаунт:"),
#         reply_markup=keyboard.accounts(page=1),
#     )


@router.callback_query(AccountsCallbackData.filter(F.action == "show_info"))
async def show_info(
    callback: CallbackQuery,
    callback_data: AccountsCallbackData,
    megafon_managers_dict: dict[int, MegafonManager],
    keyboard: InlineKeyboard,
):
    await callback.message.edit_text(
        html.bold("🔍 Получаю информацию об аккаунте...")
    )
    megafon_manager = megafon_managers_dict[callback_data.account_id]
    balance = await megafon_manager.get_balance()
    activated_numbers = await megafon_manager.get_activated_numbers()
    activated_numbers = [
        html.code(number.number) for number in activated_numbers
    ]
    activated_numbers_str = (
        (html.bold("Активные номера:\n") + "\n".join(activated_numbers))
        if activated_numbers
        else (
            html.bold("📵 Активных номеров нет\n")
            + html.bold("Дата последней деактивации:\n")
            + f"{megafon_manager.account.data.last_activate_datetime} по МСК"
        )
    )

    label_str = ""
    if megafon_manager.account.data.label:
        label_str = html.bold(f"\n📌 Метка: ") + megafon_manager.account.data.label + "\n"

    text = (
        html.bold(
            f"#{megafon_manager.account.data.account_id} | "
            + f"{megafon_manager.account.data.formated_number}\n"
        )
        + label_str
        + html.bold(f"💰 Баланс: {balance} ₽\n\n")
        + activated_numbers_str
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard.account_actions(
            callback_data.account_id, callback_data.page
        ),
    )


@router.callback_query(AccountsCallbackData.filter(F.action == "activate"))
async def activate_service_on_account(
    callback: CallbackQuery,
    callback_data: AccountsCallbackData,
    megafon_managers_dict: dict[int, MegafonManager],
    keyboard: InlineKeyboard,
):
    await callback.message.edit_text(html.bold("🔄 Подключаю номера..."))
    megafon_manager = megafon_managers_dict[callback_data.account_id]

    try:
        activated_numbers_list = await megafon_manager.activate_numbers()
    except MegafonAPIError as err:
        return await callback.message.edit_text(
            text=(
                f"#{megafon_manager.account.data.account_id} | "
                f"{megafon_manager.account.data.formated_number}\n\n"
                f"{err}"
            ),
            reply_markup=keyboard.account_actions(callback_data.account_id),
        )

    activated_numbers_str = "\n".join(activated_numbers_list)
    text = (
        html.bold(
            f"#{megafon_manager.account.data.account_id} | "
            + f"{megafon_manager.account.data.number}\n\n"
            + "✅ Только что подключенные номера:\n"
        )
        + activated_numbers_str
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard.account_actions(callback_data.account_id),
    )


@router.callback_query(AccountsCallbackData.filter(F.action == "deactivate"))
async def deactivate_service_on_account(
    callback: CallbackQuery,
    callback_data: AccountsCallbackData,
    megafon_managers_dict: dict[int, MegafonManager],
    keyboard: InlineKeyboard,
):
    await callback.message.edit_text(html.bold("🔄 Отключаю номера..."))
    megafon_manager = megafon_managers_dict[callback_data.account_id]

    try:
        await megafon_manager.delete_all_numbers()
        megafon_manager.account.data.last_activate_datetime = (
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        await megafon_manager.account.save_account_data_to_db()
    except MegafonAPIError as err:
        return await callback.message.edit_text(
            html.bold(
                "Возникла ошибка во время отключения номеров\n"
                "Попробуйте отключить снова или сделайте это позже\n"
                f"Ошибка:\n{err}"
            )
        )

    text = (
        f"#{megafon_manager.account.data.account_id} | "
        + f"{megafon_manager.account.data.number}\n\n"
        + html.bold("✅ Номера успешно отключены!\n\n")
        + html.blockquote(
            "⚠️ Но через некоторое время проверьте список "
            + "подключенных номеров, нажав кнопку «Обновить».\n"
            + "Это нужно, так как иногда мегафон просто не засчитывает отключения"
        )
    )


    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard.account_actions(callback_data.account_id),
    )


@router.callback_query(AccountsCallbackData.filter(F.action == "delete"))
async def delete_account(
    callback: CallbackQuery,
    callback_data: AccountsCallbackData,
    megafon_managers_dict: dict[int, MegafonManager],
    keyboard: InlineKeyboard,
):
    megafon_manager = megafon_managers_dict[callback_data.account_id]
    await megafon_manager.account.delete()
    keyboard.megafon_managers.remove(megafon_manager)

    text = html.bold(
        f"#{megafon_manager.account.data.account_id} | "
        + f"{megafon_manager.account.data.formated_number}\n\n"
        + "🗑️ Аккаунт успешно удалён!"
    )
    await callback.message.edit_text(
        text=text,
        reply_markup=keyboard.menu(),
    )


@router.callback_query(AccountsCallbackData.filter(F.action == "next_page"))
async def show_accounts_next_page(
    callback: CallbackQuery,
    keyboard: InlineKeyboard,
    callback_data: AccountsCallbackData,
):
    if callback_data.page > callback_data.max_page:
        return

    try:
        await callback.message.edit_text(
            html.bold("📋 Главное меню 📋 "),
            reply_markup=keyboard.menu(page=callback_data.page),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(AccountsCallbackData.filter(F.action == "prev_page"))
async def show_accounts_prev_page(
    callback: CallbackQuery,
    keyboard: InlineKeyboard,
    callback_data: AccountsCallbackData,
):
    if callback_data.page < 1:
        return
    try:
        await callback.message.edit_text(
            html.bold("📋 Главное меню 📋 "),
            reply_markup=keyboard.menu(page=callback_data.page),
        )
    except TelegramBadRequest:
        pass


@router.callback_query(AccountsCallbackData.filter(F.action == "change_proxy"))
async def change_proxy_on_account(
    callback: CallbackQuery,
    callback_data: AccountsCallbackData,
    megafon_managers_dict: dict[int, MegafonManager],
    keyboard: InlineKeyboard,
    state: FSMContext,
):
    megafon_manager = megafon_managers_dict[callback_data.account_id]
    await callback.message.edit_text(
        text=(
            html.bold("🔧 Ваш текущий прокси:\n")
            + html.code(f"{megafon_manager.account.data.proxies}\n\n")
            + html.bold(
                "📝 Если вы хотите изменить прокси, отправьте их в одном из форматов:\n"
            )
            + html.code("• user:pass@ip:port\n• ip:port")
        ),
        reply_markup=keyboard.cancel_change_proxy(callback_data.account_id),
    )
    await state.set_state(ChangeProxyStates.enter_proxy)
    await state.update_data(megafon_manager=megafon_manager)


@router.callback_query(MenuCallbackData.filter(F.action == "add_account"))
async def add_account(
    callback: CallbackQuery,
    state: FSMContext,
    database: Database,
    keyboard: InlineKeyboard,
):
    await callback.message.edit_text(
        html.bold("📝 Отправьте прокси в одном из форматов:\n\n")
        + html.code("• user:pass@ip:port\n• ip:port"),
        reply_markup=keyboard.cancel,
    )
    account_id = await database.add_account(callback.from_user.id)
    account = MegafonAccount(
        MegafonAccountData(
            account_id=account_id,
            owner_id=callback.from_user.id,
            last_activate_datetime=0,
        )
    )
    megafon_manager = MegafonManager(account)

    await state.update_data(megafon_manager=megafon_manager)
    await state.set_state(AddAccountStates.enter_proxy)


@router.callback_query(
    AccountsCallbackData.filter(F.action == "activate_on_all_accounts")
)
async def activate_service_on_all_accounts(
    callback: CallbackQuery,
    megafon_managers: list[MegafonManager],
    keyboard: InlineKeyboard,
):
    success_activation_amount = 0
    appeared_error_list = []
    success_activated_accounts: list[str] = []

    await callback.message.edit_text(
        html.bold(
            "🔄 Начинаю подключение номеров на всех аккаунтах.\n"
            + "Это может занять некоторое время..."
        )
    )

    for megafon_manager in megafon_managers:
        try:
            with logger.contextualize(account_id=megafon_manager.account.data.account_id):
                await megafon_manager.activate_numbers()
        except MegafonAPIError as err:
            appeared_error_list.append(
                html.bold(
                    f"#{megafon_manager.account.data.account_id} | "
                    f"{megafon_manager.account.data.formated_number}\n"
                )
                + f"{err}"
            )

        success_activation_amount += 1
        success_activated_accounts.append(
            html.bold(
                f"#{megafon_manager.account.data.account_id} | "
                f"{megafon_manager.account.data.formated_number}"
            )
        )
        try:
            await callback.message.edit_text(
                text=html.bold(
                    "Номера успешно активированны на "
                    f"{success_activation_amount}/{len(megafon_managers)} аккаунтов\n"
                    f"Продолжаю активацию..."
                )
            )
        except TelegramBadRequest:
            pass

    appeared_errors_str = "\n\n".join(appeared_error_list)
    text = (
        html.bold(
            f"📊 Успешно подключено {success_activation_amount} из "
            + f"{len(megafon_managers)} аккаунтов\n\n"
            "Успешно активированные аккаунты:\n\n"
        )
        + "\n".join(success_activated_accounts)
        + "\n\n"
        + "⏱️ Номера появятся на аккаунтах в течение 3 минут\n\n"
        + html.bold("❌ Ошибки возникшие при подключении:\n")
        + html.blockquote(appeared_errors_str)
    )
    await callback.message.edit_text(text, reply_markup=keyboard.menu())


@router.callback_query(
    AccountsCallbackData.filter(F.action == "deactivate_on_all_accounts")
)
async def deactivate_service_on_all_accounts(
    callback: CallbackQuery,
    megafon_managers: list[MegafonManager],
    keyboard: InlineKeyboard,
):
    success_deactivation_amount = 0
    appeared_error_list = []
    success_deactivation_accounts: list[str] = []
    await callback.message.edit_text(
        html.bold(
            "🔄 Начинаю отключение номеров на всех аккаунтах.\n"
            + "Это может занять некоторое время..."
        )
    )

    for megafon_manager in megafon_managers:
        try:
            with logger.contextualize(account_id=megafon_manager.account.data.account_id):
                await megafon_manager.delete_all_numbers()
        except MegafonAPIError as err:
            appeared_error_list.append(
                html.bold(
                    f"#{megafon_manager.account.data.account_id} | "
                    f"{megafon_manager.account.data.formated_number}\n"
                )
                + f"{err}"
            )

        megafon_manager.account.data.last_activate_datetime = (
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        await megafon_manager.account.save_account_data_to_db()
        success_deactivation_amount += 1
        success_deactivation_accounts.append(
            html.bold(
                f"#{megafon_manager.account.data.account_id} | "
                f"{megafon_manager.account.data.formated_number}"
            )
        )

        try:
            await callback.message.edit_text(
                text=html.bold(
                    f"Номера успешно деактивированны на "
                    f"{success_deactivation_amount} из {len(megafon_managers)} аккаунтов\n"
                    f"Продолжаю деактивацию..."
                )
            )
        except TelegramBadRequest:
            pass

    appeared_errors_str = "\n\n".join(appeared_error_list)
    text = (
        html.bold(
            f"📊 Успешно отключено {success_deactivation_amount} из "
            + f"{len(megafon_managers)} аккаунтов\n\n"
            "Успешно деактивированные аккаунты:\n"
        )
        + "\n".join(success_deactivation_accounts)
        + "\n\n"
        + "⏱️ Номера отключатся на аккаунтах в течение 3 минут\n\n"
        + html.bold("❌ Ошибки возникшие при отключении:\n")
        + html.blockquote(appeared_errors_str)
    )
    await callback.message.edit_text(text, reply_markup=keyboard.menu())


@router.callback_query(
    AccountsCallbackData.filter(F.action == "confirm_proxy"),
    StateFilter(ChangeProxyStates.enter_proxy),
)
async def confirm_change_proxy_on_account(
    callback: CallbackQuery,
    state: FSMContext,
    keyboard: InlineKeyboard,
    state_data: dict,
):
    megafon_manager: MegafonManager = state_data["megafon_manager"]
    await callback.message.edit_text(
        html.bold("⏳ Проверяю прокси на доступность...")
    )
    try:
        await check_proxy_availability(megafon_manager.account.data.proxies)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return await callback.message.edit_text(
            html.bold("Возникла ошибка при валидации прокси❗️\n")
            + "Если вы уверены что прокси сервер работает,\n"
            + "то обратитесь к разработчику или попробуйте ввести другие прокси",
        )
    text = html.bold(
        f"#{megafon_manager.account.data.account_id} | "
        f"{megafon_manager.account.data.formated_number}\n\n"
        f"Прокси успешно изменён на\n"
    ) + html.blockquote(megafon_manager.account.data.proxies)

    await state.clear()
    await megafon_manager.account.save_account_data_to_db()
    await callback.message.edit_text(  # type: ignore
        text=text,
        reply_markup=keyboard.account_actions(
            megafon_manager.account.data.account_id
        ),
    )


@router.callback_query(
    AddAccountCallbackData.filter(F.action == "confirm_proxy"),
    StateFilter(AddAccountStates.enter_proxy),
)
async def confirm_proxy(
    callback: CallbackQuery,
    state: FSMContext,
    keyboard: InlineKeyboard,
    state_data: dict,
):
    megafon_manager: MegafonManager = state_data["megafon_manager"]
    await callback.message.edit_text(
        html.bold("Проверяю прокси на доступность...")
    )
    # megafon_manager.account.data.proxies = ""
    # TODO
    try:
        await check_proxy_availability(megafon_manager.account.data.proxies)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        return await callback.message.edit_text(
            html.bold("Возникла ошибка при валидации прокси❗️\n")
            + "Если вы уверены что прокси сервер работает,\n"
            + "то обратитесь к разработчику или попробуйте ввести другие прокси",
        )
    await state.update_data(megafon_manager=megafon_manager)

    await callback.message.edit_text(  # type: ignore
        html.bold("Введите номер телефона (можно в любом формате)"),
        reply_markup=keyboard.cancel,
    )
    await state.set_state(AddAccountStates.enter_phone)


@router.callback_query(
    AccountsCallbackData.filter(F.action == "change_new_proxy")
)
async def change_new_proxy(
    callback: CallbackQuery,
    state: FSMContext,
    keyboard: InlineKeyboard,
    callback_data: AccountsCallbackData,
):
    await state.set_state(ChangeProxyStates.enter_proxy)
    await callback.message.edit_text(  # type: ignore
        html.bold("Отправьте прокси в одном из форматов:\n")
        + "1. user:pass@ip:port\n"
        + "2. ip:port",
        reply_markup=keyboard.cancel_change_proxy(callback_data.account_id),
    )


@router.callback_query(
    AddAccountCallbackData.filter(F.action == "change_proxy")
)
async def change_proxy_while_add_account(
    callback: CallbackQuery,
    state: FSMContext,
    keyboard: InlineKeyboard,
):
    await state.set_state(AddAccountStates.enter_proxy)
    await callback.message.edit_text(  # type: ignore
        "Отправьте прокси в одном из форматов:\n"
        + "1. user:pass@ip:port\n"
        + "2. ip:port",
        reply_markup=keyboard.cancel,
    )


@router.callback_query(AddAccountCallbackData.filter(F.action == "resend_otp"))
async def resend_otp(
    callback: CallbackQuery,
    state: FSMContext,
    state_data: dict,
    keyboard: InlineKeyboard,
):
    megafon_manager: MegafonManager = state_data["megafon_manager"]

    await callback.message.edit_text(
        text=html.bold("Обрабатываю запрос, подождите..."),
        reply_markup=keyboard.otp,
    )

    try:
        await megafon_manager.send_otp()
    except MegafonAPIError as err:
        await callback.message.edit_text(
            f"Не удалось отправить код так как: {err}",
            reply_markup=keyboard.otp,
        )
        return

    await callback.message.edit_text(
        text=html.bold("Введите код отправленный в СМС:"),
        reply_markup=keyboard.otp,
    )


@router.callback_query(AccountsCallbackData.filter(F.action == "change_label"))
async def change_label_on_account(
    callback: CallbackQuery,
    callback_data: AccountsCallbackData,
    megafon_managers_dict: dict[int, MegafonManager],
    keyboard: InlineKeyboard,
    state: FSMContext,
):
    megafon_manager = megafon_managers_dict[callback_data.account_id]
    current_label = megafon_manager.account.data.label or "не установлена"
    await callback.message.edit_text(
        text=(
            html.bold("🔧 Ваша текущая метка:\n")
            + html.code(f"{current_label}\n\n")
            + html.bold("📝 Отправьте новую метку или нажмите «Отмена»")
        ),
        reply_markup=keyboard.cancel_change_label(callback_data.account_id),
    )
    await state.set_state(ChangeLabelStates.enter_label)
    await state.update_data(megafon_manager=megafon_manager)


# async def _show_account_info(
#     callback: CallbackQuery,
#     index: int,
#     accounts: dict[int, MegafonAccount],
#     keyboard: InlineKeyboard,
# ) -> bool:
#     account = accounts.get(index)
#     if account is None:
#         await callback.answer("Аккаунт не найден", show_alert=True)
#         return False

#     await callback.message.edit_text("Обрабатываю запрос, подождите...")

#     api = MegafonAPI(account)
#     try:
#         balance = await api.get_balance()
#         activated_numbers = await api.get_activated_numbers()
#     except MegafonAPIError as err:
#         await callback.answer(
#             f"Ошибка при получении данных аккаунта: {err}", show_alert=True
#         )
#         return False

#     if activated_numbers:
#         numbers_list = "\n".join(
#             f"`{number_info.number}`" for number_info in activated_numbers
#         )
#         numbers_text = f"Активные номера:\n{numbers_list}"
#     else:
#         numbers_text = "Активных номеров нет"

#     phonenumbers.parse(account.number, "RU")

#     text = (
#         f"Аккаунт {account.account_id}\n"
#         f"Номер: {account.number}\n"
#         f"Баланс: {balance} ₽\n\n"
#         f"{numbers_text}"
#     )
#     await callback.message.edit_text(
#         text,
#         reply_markup=keyboard.account_actions(index),
#         parse_mode=ParseMode.MARKDOWN_V2,
#     )
#     return True


# @router.callback_query(F.data == "add_account")
# async def add_account_handler(
#     callback: CallbackQuery,
#     state: FSMContext,
#     keyboard: InlineKeyboard,
# ) -> None:
#     await state.set_state(AddAccountStates.enter_proxy)
#     await callback.message.edit_text(  # type: ignore
#         "Отправьте прокси в формате user:pass@ip:port",
#         reply_markup=keyboard.cancel,
#     )
#     await callback.answer()


# @router.callback_query(F.data == "cancel")
# async def cancel_handler(
#     callback: CallbackQuery,
#     state: FSMContext,
#     keyboard: InlineKeyboard,
# ) -> None:
#     data = await state.get_data()
#     account: MegafonAccount | None = data.get("account")

#     if isinstance(account, MegafonAccount):
#         try:
#             account.delete()
#         except OSError:
#             # Если файла уже нет или не удалился — просто игнорируем
#             pass

#     await state.clear()
#     await callback.message.edit_text(  # type: ignore
#         "Выберите аккаунт:",
#         reply_markup=keyboard.start,
#     )
#     await callback.answer("Действие отменено")


# @router.callback_query(F.data == "connect_all")
# async def connect_all_handler(callback: CallbackQuery) -> None:
#     await callback.answer(
#         "Подключить везде: функционал ещё не реализован", show_alert=True
#     )


# @router.callback_query(F.data == "disconnect_all")
# async def disconnect_all_handler(callback: CallbackQuery) -> None:
#     await callback.answer(
#         "Отключить везде: функционал ещё не реализован", show_alert=True
#     )


# @router.callback_query(F.data == "resend_otp")
# async def resend_otp_handler(
#     callback: CallbackQuery, state: FSMContext
# ) -> None:
#     data = await state.get_data()
#     api: MegafonAPI | None = data.get("api")

#     if api is None:
#         await callback.answer(
#             "Нет активного процесса добавления аккаунта", show_alert=True
#         )
#         return

#     await callback.message.answer("Обрабатываю запрос, подождите...")  # type: ignore

#     try:
#         await api.send_otp()
#     except MegafonAPIError as err:
#         await callback.answer(
#             f"Не удалось отправить код: {err}", show_alert=True
#         )
#         return

#     await callback.answer("Код отправлен повторно")


# @router.callback_query(F.data == "change_proxy")
# async def change_proxy_handler(
#     callback: CallbackQuery,
#     state: FSMContext,
#     keyboard: InlineKeyboard,
# ) -> None:
#     await state.update_data(proxy_raw=None)
#     await state.set_state(AddAccountStates.enter_proxy)
#     await callback.message.edit_text(  # type: ignore
#         "Отправьте прокси в формате user:pass@ip:port",
#         reply_markup=keyboard.cancel,
#     )
#     await callback.answer()


# @router.callback_query(F.data.startswith("account:"))
# async def account_info_handler(
#     callback: CallbackQuery,
#     accounts: dict[int, MegafonAccount],
#     keyboard: InlineKeyboard,
# ) -> None:
#     data = callback.data or ""
#     _, _, index_str = data.partition(":")

#     if not index_str.isdigit():
#         await callback.answer("Некорректный выбор аккаунта", show_alert=True)
#         return

#     index = int(index_str)
#     ok = await _show_account_info(callback, index, accounts, keyboard)
#     if not ok:
#         return

#     await callback.answer()


# @router.callback_query(F.data == "back_to_accounts")
# async def back_to_accounts_handler(
#     callback: CallbackQuery,
#     keyboard: InlineKeyboard,
# ) -> None:
#     await callback.message.edit_text(
#         "Выберите аккаунт:",
#         reply_markup=keyboard.start,
#     )
#     await callback.answer()


# @router.callback_query(F.data.startswith("account_activate:"))
# async def account_activate_handler(
#     callback: CallbackQuery,
#     accounts: dict[int, MegafonAccount],
#     keyboard: InlineKeyboard,
# ) -> None:
#     data = callback.data or ""
#     _, _, index_str = data.partition(":")

#     if not index_str.isdigit():
#         await callback.answer("Некорректный выбор аккаунта", show_alert=True)
#         return

#     index = int(index_str)
#     account = accounts.get(index)
#     if account is None:
#         await callback.answer("Аккаунт не найден", show_alert=True)
#         return

#     api = MegafonAPI(account)
#     await callback.message.edit_text("Обрабатываю запрос, подождите...")
#     try:
#         await api.activate_numbers()
#     except MegafonAPIError as err:
#         await callback.answer(
#             f"Не удалось подключить номера: {err}", show_alert=True
#         )
#         return
#     await callback.answer("Номера подключены")

#     ok = await _show_account_info(callback, index, accounts, keyboard)
#     if not ok:
#         return


# @router.callback_query(F.data.startswith("account_delete:"))
# async def account_delete_handler(
#     callback: CallbackQuery,
#     accounts: dict[int, MegafonAccount],
#     keyboard: InlineKeyboard,
# ) -> None:
#     data = callback.data or ""
#     _, _, index_str = data.partition(":")

#     if not index_str.isdigit():
#         await callback.answer("Некорректный выбор аккаунта", show_alert=True)
#         return

#     index = int(index_str)
#     account = accounts.get(index)
#     if account is None:
#         await callback.answer("Аккаунт не найден", show_alert=True)
#         return

#     try:
#         account.delete()
#     except OSError as err:
#         await callback.answer(
#             f"Не удалось удалить аккаунт: {err}", show_alert=True
#         )
#         return

#     await callback.message.edit_text(
#         "Выберите аккаунт:",
#         reply_markup=keyboard.start,
#     )
#     await callback.answer("Аккаунт удалён")


# @router.callback_query(F.data.startswith("account_disconnect:"))
# async def account_disconnect_handler(
#     callback: CallbackQuery,
#     accounts: dict[int, MegafonAccount],
#     keyboard: InlineKeyboard,
# ) -> None:
#     data = callback.data or ""
#     _, _, index_str = data.partition(":")

#     if not index_str.isdigit():
#         await callback.answer("Некорректный выбор аккаунта", show_alert=True)
#         return

#     index = int(index_str)
#     account = accounts.get(index)
#     if account is None:
#         await callback.answer("Аккаунт не найден", show_alert=True)
#         return

#     api = MegafonAPI(account)
#     await callback.message.edit_text("Обрабатываю запрос, подождите...")
#     try:
#         await api.delete_all_numbers()
#     except MegafonAPIError as err:
#         await callback.answer(
#             f"Не удалось отключить номера: {err}", show_alert=True
#         )
#         return
#     await callback.answer("Номера отключены")

#     ok = await _show_account_info(callback, index, accounts, keyboard)
#     if not ok:
#         return
