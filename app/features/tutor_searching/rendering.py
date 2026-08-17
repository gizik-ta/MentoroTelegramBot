from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from features.common.keyboards import CommonKeyboards
from features.user_menu.keyboards import UserMenuKeyboards

from .keyboards import TutorSearchingKeyboards
from .texts import TutorSearchingTexts


class TutorSearchingViews:
    @staticmethod
    def title() -> tuple[str, ReplyKeyboardMarkup]:
        return TutorSearchingTexts.TITLE, UserMenuKeyboards.back_to_menu_keyboard()

    @staticmethod
    def subject() -> tuple[str, InlineKeyboardMarkup]:
        return (
            TutorSearchingTexts.CHOOSE_SUBJECT,
            CommonKeyboards.choose_subject_keyboard(),
        )

    @staticmethod
    def info_message(
        subject: str, current_filters: list | None = None
    ) -> tuple[str, InlineKeyboardMarkup]:
        if current_filters is None:
            current_filters = []
        text = TutorSearchingTexts.info_message_processing(subject)
        keyboard = TutorSearchingKeyboards.set_filters_keyboard(current_filters)

        return text, keyboard

    @staticmethod
    def filters_prompts(filter_name: str) -> tuple[str, InlineKeyboardMarkup | None]:
        text = TutorSearchingTexts.FILTER_PROMPTS.get(filter_name, "")
        match filter_name:
            case "price":
                keyboard = None
            case "classes_format":
                keyboard = CommonKeyboards.choose_classes_format()
            case "teaching_type":
                keyboard = CommonKeyboards.choose_teaching_type()
            case _:
                keyboard = None

        return text, keyboard

    @staticmethod
    def header_text(subject_key: str, active_filters: dict) -> str:
        return TutorSearchingTexts.header_text(subject_key, active_filters)

    @staticmethod
    def contact_info_text(username: str | None) -> str:
        return TutorSearchingTexts.contact_info_text(username)

    @staticmethod
    def ad_position(current_index: int, total_count: int) -> str:
        return TutorSearchingTexts.ad_position(current_index, total_count)
