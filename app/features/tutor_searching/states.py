from aiogram.fsm.state import State, StatesGroup


class TutorSearch(StatesGroup):
    subject_processing = State()
    set_filters = State()
    price_filter = State()
    classes_format_filter = State()
    teaching_type_filter = State()
