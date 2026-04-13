from aiogram.fsm.state import State, StatesGroup


class ChangeProxyStates(StatesGroup):
    enter_proxy = State()


class ChangeLabelStates(StatesGroup):
    enter_label = State()
