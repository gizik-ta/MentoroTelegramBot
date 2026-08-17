from typing import ClassVar


class CommonTexts:
    OWNER_ADS_TITLE = "Мои объявления"
    OWNER_ADS_DESCRIPTION = "Здесь ты можешь управлять своими объявлениями."
    CREATE_AD_BUTTON = "Создать объявление"
    BACK_TO_MENU_BUTTON = "Назад в меню"
    BUY_AD_BUTTON = "ОПЛАТИТ ОБЪЯВЛЕНИЕ"
    RENEW_AD_BUTTON = "Продлить публикацию"
    DELETE_AD_BUTTON = "Удалить объявление"
    EDIT_AD_BUTTON = "Редактировать объявление"

    # Subjects Mapping
    SUBJECTS: ClassVar[dict[str, str]] = {
        "math": "Математика",
        "physics": "Физика",
        "chemistry": "Химия",
        "biology": "Биология",
        "history": "История",
        "geography": "География",
        "russian": "Русский язык",
        "english": "Английский язык",
        "sociology": "Обществознание",
        "literature": "Литература",
        "informatics": "Информатика",
    }

    # Teaching Types Mapping
    TEACHING_TYPES: ClassVar[dict[str, str]] = {
        "exam_preperation": "Подготовка к экзамену",
        "education_help": "Подтянуть успеваемость",
        "olympiads_preperation": "Олимпиадная подготовка",
        "do_not_specify": "Не уточнять",
    }

    # Classes Format Mapping
    CLASSES_FORMATS: ClassVar[dict[str, str]] = {
        "online": "Онлайн",
        "offline": "Очно",
        "both": "Оба варианта",
    }

    BUTTON_TRANSLATIONS: ClassVar[dict[str, str]] = {
        "payment_waiting": "ОЖИДАЕТ ОПЛАТЫ",
        "on_check": "НА ПРОВЕРКЕ",
        "published": "ОПУБЛИКОВАНО",
        "rejected": "ОТКЛОНЕНО",
        "online": "Онлайн",
        "offline": "Офлайн",
        "both": "Онлайн и Офлайн",
        "education_help": "Подтянуть успеваемость",
        "olympiads_preperation": "Олимпиадная подготовка",
        "exam_preperation": "Подготовка к экзамену",
        "do_not_specify": "Не уточнять",
        "math": "Математика",
        "physics": "Физика",
        "english": "Английский язык",
        "chemistry": "Химия",
        "informatics": "Информатика",
        "biology": "Биология",
        "history": "История",
    }

    # UI Prompts & Card Formatting Templates
    CONFIRM_AD_PROMPT: str = (
        "✅ Проверь данные объявления:\n\n"
        "{ad_text}\n\n"
        "⬇️ Подтверди публикацию или измени поле через кнопки ниже."
    )
    EDIT_FIELDS_PROMPT: str = "Редактировать поля:"
    NO_NAME_PLACEHOLDER: str = "—"

    STATUS_HEADER_TEMPLATE: str = "<b>📌 СТАТУС: {status}</b>\n\n"
    PUBLISHED_UNTIL_TEMPLATE: str = "ОПУБЛИКОВАНО ДО {publishing_end}"

    AD_TEMPLATE: str = (
        "👤 Репетитор: {tutor_name}\n"
        "📚 Предмет: {tutor_subject}\n"
        "🎯 Цель: {tutor_type}\n"
        "🏆 Опыт и Достижения:\n"
        "<blockquote expandable>{tutor_experience}</blockquote>\n"
        "💻 Формат занятий: {tutor_format}\n"
        "💰 Стоимость занятий: {tutor_price} ₽/час\n\n"
        "Текст объявления:\n<blockquote expandable>{tutor_description}</blockquote>"
    )

    STATISTICS_TEMPLATE: str = (
        "\n\n<b>Статистика:</b>\n"
        "- Количество просмотров: {views}\n"
        "- Количество лайков: {likes}"
    )

    BTN_LIKE = "❤️ Сохранить"
    BTN_LIKED = "❤️ Сохранено!"
    BTN_CONTACT = "📝 Написать"

    TOAST_SAVED = "❤️ Сохранено!"
    TOAST_REMOVED = "💔 Удалено из избранного"

    @classmethod
    def like_button_text(cls, is_liked: bool) -> str:
        return cls.BTN_LIKED if is_liked else cls.BTN_LIKE
