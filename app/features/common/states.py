from aiogram.fsm.state import State, StatesGroup


class BotFlow(StatesGroup):
    menu_navigation = State()
    tutor_search = State()
    my_ads = State()
    notifications = State()
    help = State()
    card_making = State()
    saved_ads = State()


class CardMaking(StatesGroup):
    tutor_name = State()
    tutor_photo = State()
    tutor_photo_confirm = State()
    tutor_subject = State()
    tutor_teaching_type = State()
    tutor_experience = State()
    tutor_classes_format = State()
    tutor_description = State()
    tutor_price = State()
    tutor_confirm = State()
