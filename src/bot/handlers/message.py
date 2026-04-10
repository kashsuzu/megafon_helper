import html

import phonenumbers
from aiogram import Router, html
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.bot.fsm.add_account import AddAccountStates
from src.bot.fsm.change_proxy import ChangeProxyStates
from src.bot.keyboard.inline import InlineKeyboard
from src.bot.utils import format_phone_number, proxy_format_is_valid
from src.megafon.exceptions import IncorrectOTPCode, MegafonAPIError
from src.megafon.manager import MegafonManager

router = Router()


@router.message(Command("start"))
async def start(
    message: Message,
    keyboard: InlineKeyboard,
) -> None:
    await message.answer(
        text=(html.bold("📋 Главное меню 📋")),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard.menu(),
    )


@router.message(
    StateFilter(AddAccountStates.enter_proxy, ChangeProxyStates.enter_proxy)
)
async def proccess_proxy(
    message: Message,
    state: FSMContext,
    keyboard: InlineKeyboard,
    state_data: dict,
):
    raw = (message.text or "").strip()

    if not proxy_format_is_valid(raw):
        return await message.answer(
            html.bold("❌ Некорректный формат прокси!\n\n")
            + "📝 Ожидаемый формат:\n"
            + html.code("• user:pass@ip:port\n• ip:port"),
            reply_markup=keyboard.cancel,
        )

    # Разбор прокси на части
    user = password = "-"
    if "@" in raw:
        creds, host_part = raw.split("@", 1)
        user, password = creds.split(":", 1)
    else:
        host_part = raw

    ip, port = host_part.rsplit(":", 1)

    text = (
        html.bold("🔍 Проверьте прокси:\n\n")
        + "👤 Пользователь: "
        + html.code(user)
        + "\n"
        + "🔑 Пароль: "
        + html.code(password)
        + "\n"
        + "🌐 Адрес: "
        + html.code(ip)
        + "\n"
        + "🔌 Порт: "
        + html.code(port)
        + "\n\n"
        + "✅ Если всё верно, нажмите «Подтвердить»\n"
        + "✏️ Иначе — «Изменить»"
    )

    megafon_manager: MegafonManager = state_data["megafon_manager"]
    megafon_manager.account.data.proxies = f"http://{raw}"
    await state.update_data(megafon_manager=megafon_manager)

    if await state.get_state() == AddAccountStates.enter_proxy.state:
        reply_markup = keyboard.confirm_proxy
    else:
        reply_markup = keyboard.confirm_change_proxy(
            megafon_manager.account.data.account_id
        )

    await message.answer(
        text,
        reply_markup=reply_markup,
    )


@router.message(StateFilter(AddAccountStates.enter_phone))
async def proccess_phone(
    message: Message,
    state: FSMContext,
    keyboard: InlineKeyboard,
    state_data: dict,
):
    raw = (message.text or "").strip()

    parsed = phonenumbers.parse(raw, "RU")
    if not phonenumbers.is_valid_number(parsed):
        return await message.answer(
            html.bold("❌ Некорректный номер телефона!\n\n")
            + "📱 Введите номер ещё раз:",
            reply_markup=keyboard.cancel,
        )
    message = await message.answer(
        html.bold("⏳ Обрабатываю запрос, подождите...")
    )

    local_number = str(parsed.national_number)
    megafon_manager: MegafonManager = state_data["megafon_manager"]
    megafon_manager.account.data.number = local_number
    await state.update_data(
        megafon_manager=megafon_manager,
    )

    try:
        await megafon_manager.send_otp()
    except MegafonAPIError as err:
        return await message.edit_text(
            html.bold("❌ Не удалось отправить код\n\n") + f"Ошибка: {err}",
            reply_markup=keyboard.cancel,
        )

    await message.edit_text(
        html.bold("📩 Введите код, отправленный в СМС"),
        reply_markup=keyboard.otp,
    )
    await state.set_state(AddAccountStates.enter_code)


@router.message(StateFilter(AddAccountStates.enter_code))
async def process_code(
    message: Message,
    state: FSMContext,
    keyboard: InlineKeyboard,
    state_data: dict,
):
    code = (message.text or "").strip()

    if not code.isdigit():
        return await message.answer(
            html.bold("❌ Код должен состоять только из цифр\n\n")
            + "🔢 Введите код ещё раз:",
            reply_markup=keyboard.otp,
        )

    megafon_manager: MegafonManager = state_data["megafon_manager"]

    message = await message.answer(
        text=html.bold("⏳ Обрабатываю запрос, подождите...")
    )

    try:
        await megafon_manager.submit_otp(code)
        await megafon_manager.update_tokens()
    except IncorrectOTPCode:
        await message.edit_text(
            html.bold("❌ Неверный код!\n\n") + "🔄 Попробуйте ещё раз",
            reply_markup=keyboard.otp,
        )
        return
    except MegafonAPIError as err:
        await message.edit_text(
            html.bold("❌ Ошибка при проверке кода\n\n") + f"Ошибка: {err}",
            reply_markup=keyboard.otp,
        )
        return

    megafon_manager.account.data.formated_number = format_phone_number(
        megafon_manager.account.data.number
    )
    await megafon_manager.account.save_account_data_to_db()
    keyboard.remove_megafon_managers_by_account_id(
        megafon_manager.account.data.account_id
    )
    keyboard.megafon_managers.append(megafon_manager)
    await message.edit_text(
        html.bold("✅ Аккаунт успешно добавлен!"),
        reply_markup=keyboard.menu(),
    )
    await state.clear()
