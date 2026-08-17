from features.ad_making.callbacks import ConfirmAdCallback
from features.ad_making.keyboards import AdMakingKeyboards
from features.ad_making.texts import AdMakingTexts


def test_final_creation_confirmation_has_inline_cancel_and_confirm():
    keyboard = AdMakingKeyboards.confirm_ad(is_editing=False)
    buttons = keyboard.inline_keyboard[0]

    assert [button.text for button in buttons] == [
        AdMakingTexts.CANCEL_BUTTON,
        AdMakingTexts.CONFIRM_BUTTON,
    ]
    assert ConfirmAdCallback.unpack(buttons[0].callback_data).action == "cancel"
    assert ConfirmAdCallback.unpack(buttons[1].callback_data).action == "confirm"


def test_confirmation_reply_keyboard_contains_only_editing_options():
    keyboard = AdMakingKeyboards.change_input()
    button_texts = [
        button.text
        for row in keyboard.keyboard
        for button in row
    ]

    assert AdMakingTexts.CANCEL_BUTTON not in button_texts
    assert button_texts == [
        AdMakingTexts.FIELD_NAME_BUTTON,
        AdMakingTexts.FIELD_PHOTO_BUTTON,
        AdMakingTexts.FIELD_SUBJECT_BUTTON,
        AdMakingTexts.FIELD_DIRECTION_BUTTON,
        AdMakingTexts.FIELD_EXPERIENCE_BUTTON,
        AdMakingTexts.FIELD_FORMAT_BUTTON,
        AdMakingTexts.FIELD_PRICE_BUTTON,
        AdMakingTexts.FIELD_DESCRIPTION_BUTTON,
    ]
