from typing import ClassVar

from common.data.filters import FILTERS
from features.common.rendering import translate
from features.common.texts import CommonTexts


class TutorSearchingTexts:
    # Titles & Prompts
    TITLE = "👨‍🏫 Поиск репетитора"
    CHOOSE_SUBJECT = "📚 По какому предмету ты ищешь репетитора?"
    MAIN_MENU_TITLE = "Главное меню"
    INVALID_PRICE_INPUT = "⚠️ Введите корректную сумму числом."
    EMPTY_SEARCH_RESULTS = (
        "<b>🙈 Объявлений по этим критериям не найдено.</b>\n"
        "Попробуйте изменить или сбросить фильтры."
    )
    AD_POSITION_TEMPLATE = "<b>{current}/{total}</b>\n\n"

    # Toast Notifications
    TOAST_SAVED = "❤️ Сохранено!"
    TOAST_REMOVED = "💔 Удалено из избранного"

    FILTER_PROMPTS: ClassVar[dict[str, str]] = {
        "price": "💵 Какая максимальная стоимость услуги (₽/час)?",
        "classes_format": "💻 Выбери удобный формат занятий:",
        "teaching_type": "🎯 Какая у тебя цель занятий?",
    }

    # Keyboard Button Labels & Icons
    BTN_PREV = "⬅️"
    BTN_NEXT = "➡️"
    BTN_LIKE = "❤️ Сохранить"
    BTN_LIKED = "❤️ Сохранено!"
    BTN_CONTACT = "📝 Написать"
    FILTER_ACTIVE_PREFIX = "❌ "

    @classmethod
    def filter_button_text(cls, filter_label: str, is_active: bool) -> str:
        return (
            f"{cls.FILTER_ACTIVE_PREFIX}{filter_label}" if is_active else filter_label
        )

    @classmethod
    def like_button_text(cls, is_liked: bool) -> str:
        return cls.BTN_LIKED if is_liked else cls.BTN_LIKE

    @staticmethod
    def info_message_processing(subject_key: str) -> str:
        subject_name = CommonTexts.SUBJECTS.get(subject_key, "")
        return (
            f"📚 <b>Объявления по предмету «{subject_name}»</b>\n\n"
            "Ниже собраны актуальные предложения по выбранному предмету.\n"
            'Лайкнутые объявления будут в разделе <b>"Сохраненные объявления"</b>.\n\n'
            "🔄 Используй кнопки под сообщением, чтобы листать объявления.\n"
            "🎯 Чтобы уточнить поиск, выбери нужные фильтры из списка ниже."
        )

    @staticmethod
    def header_text(subject_key: str, active_filters: dict) -> str:
        subject_name = CommonTexts.SUBJECTS.get(subject_key, "")

        filter_lines = []
        for flt_key, flt_val in active_filters.items():
            if flt_val is not None:
                label = FILTERS.get(flt_key, flt_key)
                translated_val = translate(flt_val) or "-"
                filter_lines.append(f"• <b>{label}:</b> {translated_val}")

        filters_block = "\n".join(filter_lines) if filter_lines else "<i>Не выбраны</i>"

        return (
            f"📚 <b>Объявления по предмету «{subject_name}»</b>\n\n"
            "Ниже собраны актуальные предложения по выбранному предмету.\n"
            "Понравившиеся объявления будут доступны в разделе "
            '"Сохраненные объявления".\n\n'
            "🔄 Используй кнопки под сообщением, чтобы листать карточки.\n"
            "🎯 Чтобы уточнить поиск, выбери нужные фильтры из списка ниже.\n\n"
            f"<b>Примененные фильтры:</b>\n{filters_block}"
        )

    @staticmethod
    def contact_info_text(username: str | None) -> str:
        if username:
            return f"📝 Свяжись с репетитором: @{username}"
        return (
            "😥 У репетитора не указан username.\n"
            "Попробуй найти контактную информацию в тексте объявления."
        )

    @classmethod
    def ad_position(cls, current_index: int, total_count: int) -> str:
        return cls.AD_POSITION_TEMPLATE.format(
            current=current_index + 1,
            total=total_count,
        )
