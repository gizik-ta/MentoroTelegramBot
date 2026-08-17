from features.common.texts import CommonTexts


class MyAdsTexts:
    TITLE = CommonTexts.OWNER_ADS_TITLE
    DESCRIPTION = CommonTexts.OWNER_ADS_DESCRIPTION
    NOT_FOUND = "Объявление не найдено."
    RENEW_NOT_AVAILABLE = "Продление недоступно для этого объявления."
    DELETE_CONFIRMATION = "\n\n Это объявление будет удалено навсегда. Продолжить?"
    DELETE_SUCCESS = "Объявление успешно удалено."

    DELETE_BUTTON = CommonTexts.DELETE_AD_BUTTON
    CANCEL_BUTTON = "Отменить"
    PAYMENT_BUTTON = "💳 Оплатить 200₽ (YooMoney)"
    PAYMENT_DESCRIPTION = "Публикация объявления на месяц."
    RENEWAL_PAYMENT_DESCRIPTION = "Продление публикации объявления ещё на месяц."
    INITIAL_PAYMENT_PURPOSE = (
        "Вы оплачиваете публикацию объявления на 30 дней. "
        "После оплаты, ваше объявление будет доступно для просмотра ученикам."
    )
    RENEWAL_PAYMENT_PURPOSE = (
        "Вы оплачиваете продление публикации объявления еще на месяц"
    )
    PAYMENT_MESSAGE_TEMPLATE = (
        "💳 Нажмите на кнопку ниже, чтобы перейти к оплате:"
        "<details open>"
        "<summary> За что я плачу? </summary>"
        "<p>{purpose}</p>"
        "</details>"
        "<details>"
        "<summary> А это безопасно? </summary>"
        "<p> Для оплаты используется защищенная система "
        "<a href='https://yoomoney.ru'>YooMoney</a> "
        "разработанная <b>Яндексом</b>.</p>"
        "</details>"
    )
    PAYMENT_MESSAGE = PAYMENT_MESSAGE_TEMPLATE.format(purpose=INITIAL_PAYMENT_PURPOSE)
    RENEWAL_PAYMENT_MESSAGE = PAYMENT_MESSAGE_TEMPLATE.format(
        purpose=RENEWAL_PAYMENT_PURPOSE
    )
    PUBLICATION_END_REMINDER = (
        "Подходит к концу оплаченный срок публикации. "
        "Ты можешь продлить его в разделе Мои объявления"
    )
