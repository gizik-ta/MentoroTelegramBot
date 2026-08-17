from features.common.texts import CommonTexts


class AdMakingTexts:
    CREATE_BUTTON = CommonTexts.CREATE_AD_BUTTON
    CANCEL_BUTTON = "❌ Отменить создание"
    CANCEL_EDITING_BUTTON = "❌ Отменить изменение"

    PHOTO_SAVE_BUTTON = "➡ Сохранить фото"
    NEXT_QUESTION_BUTTON = "➡ Следующий вопрос"
    ADD_PHOTO_BUTTON = "📷 Добавить фото"
    RESELECT_PHOTO_BUTTON = "🔄 Выбрать заново"
    CONFIRM_BUTTON = "✅ Подтвердить"

    FIELD_NAME_BUTTON = "👤 ФИО"
    FIELD_PHOTO_BUTTON = "📷 Фото"
    FIELD_SUBJECT_BUTTON = "📚 Предмет"
    FIELD_DIRECTION_BUTTON = "🎯 Направление"
    FIELD_EXPERIENCE_BUTTON = "🏆 Опыт"
    FIELD_FORMAT_BUTTON = "💻 Формат"
    FIELD_PRICE_BUTTON = "💰 Стоимость"
    FIELD_DESCRIPTION_BUTTON = "📝 Описание"

    CREATE_TITLE = "📝 Создание объявления\n\n"
    EDIT_TITLE = "Изменение информации"
    OWNER_ADS_TITLE = CommonTexts.OWNER_ADS_TITLE
    OWNER_ADS_DESCRIPTION = CommonTexts.OWNER_ADS_DESCRIPTION

    NAME_PROMPT = "1/8 Укажи своё полное имя:\nФамилия Имя Отчество"
    NAME_INVALID = "❌ Нужно указать:\nФамилия Имя Отчество"

    PHOTO_PROMPT = (
        "📷 <b>2/8 Прикрепи до 6 фотографий.</b>\n\n"
        "Лучше, если на фото будет видно лицо. "
        "Так у учеников будет больше доверия к тебе.\n"
        "Также сюда можно прикрепить оформелнные слайды с информацией "
        "или подтверждение своих достижений."
    )
    PHOTO_ONE_BY_ONE = "❌ Отправляй фото по одному."
    PHOTO_MAXIMUM = "❌ Максимум 6 фото."
    PHOTO_REUPLOAD = "📷 Загрузи фотографии заново."
    PHOTO_NEXT = "📷 Отправь следующее фото."

    SUBJECT_PROMPT = "📚 <b>3/8 Выбери предмет:</b>"
    TEACHING_TYPE_PROMPT = "🎯 <b>4/8 Выбери направление:</b>"
    EXPERIENCE_PROMPT = (
        "🏆 <b>5/8 Опиши свои достижения и опыт.</b>\n\n"
        "Лучше избегать общих фраз, а указывать конкретные результаты. "
        "Так будет лечге заинтересовать учеников.\n\n"
        "<u>Например</u>: «Подготовил 10 учеников к ЕГЭ по математике, "
        "средний балл 85+» или «Являюсь победителем/призером олимпиады»."
    )
    EXPERIENCE_INVALID = (
        "❌ С более подробным описанием будет больше шансов привлечь учеников. "
        "Напиши не менее 20 символов."
    )
    CLASSES_FORMAT_PROMPT = "💻 6/8 Формат занятий:"
    PRICE_PROMPT = "💰 7/8 Укажи стоимость (₽/час)."
    PRICE_INVALID = "❌ Нужно ввести натуральное число. Попробуй снова.\nПример: 1500"
    PRICE_TOO_LARGE = "❌ Слишком большая сумма. Попробуй снова.\nПример: 1500"
    DESCRIPTION_PROMPT = (
        "📝 <b>8/8 Напиши текст объявления.</b>"
        "В нем стоит подсветить преимущества работы с тобой и условия, "
        "которые ты предлагаешь. "
        "Чем подробнее, тем лучше!"
    )
    DESCRIPTION_INVALID = "❌ Слишком короткое описание (минимум 50 символов)."

    EDIT_NAME_PROMPT = "1/8 Укажи своё полное имя:\nИмя Фамилия Отчество"
    EDIT_PHOTO_PROMPT = "📷 Прикрепи до 5 фотографий."
    EDIT_SUBJECT_PROMPT = "📚 Выбери предмет:"
    EDIT_DIRECTION_PROMPT = "🎯 Выбери направление:"
    EDIT_EXPERIENCE_PROMPT = "🏆 Опиши свой опыт."
    EDIT_FORMAT_PROMPT = "💻 Формат занятий:"
    EDIT_PRICE_PROMPT = "💰 Укажи стоимость (₽/час)."
    EDIT_DESCRIPTION_PROMPT = "📝 Напиши текст объявления (минимум 50 символов)."

    CREATION_CANCELLED = "❌ Создание объявления отменено."
    EDITING_CANCELLED = "❌ Изменение объявления отменено."
    EDITING_COMPLETED = "✅ Изменение объявления завершено."
    CREATED = "✅ Объявление создано и ожидает оплаты."
    UPDATED_PENDING_REVIEW = (
        "✅ Информация объявления была обновлена и ожидает проверки."
    )
    UPDATED_PENDING_PAYMENT = (
        "✅ Информация объявления была обновлена и ожидает оплаты."
    )
    NOT_FOUND = "Объявление не найдено."

    @staticmethod
    def photo_count(amount: int) -> str:
        return f"📷 Фото {amount} из 6 сохранено."
