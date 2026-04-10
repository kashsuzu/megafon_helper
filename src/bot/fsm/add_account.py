from aiogram.fsm.state import State, StatesGroup


class AddAccountStates(StatesGroup):
    enter_proxy = State()
    enter_phone = State()
    enter_code = State()

