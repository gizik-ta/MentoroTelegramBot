from aiogram.fsm.state import State, StatesGroup


class AdminFlow(StatesGroup):
    menu_navigation = State()
    ad_checking = State()
    rejection_reason = State()
    statistics = State()
    notifications = State()
