from datetime import date
from html import escape

from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InputMediaPhoto, Message

from .models import TutorAd
from .texts import CommonTexts

TEXT_LIMIT = 4096


def translate(val: str | list[str] | tuple[str, ...]) -> str | list[str]:
    if not val:
        return CommonTexts.NO_NAME_PLACEHOLDER
    try:
        if isinstance(val, (list, tuple)):
            return [
                CommonTexts.BUTTON_TRANSLATIONS.get(v.lower().strip(), v) for v in val
            ]
        return CommonTexts.BUTTON_TRANSLATIONS.get(val.lower().strip(), val)
    except AttributeError:
        return val


def render_message(
    ad: TutorAd,
    is_pro: bool = False,
    show_statistic: bool = False,
    show_state: bool = False,
    show_publication_end: bool = False,
) -> str:
    if is_pro:
        body_text = ""
    else:
        if isinstance(ad.tutor_name, (list, tuple)):
            raw_name = " ".join(ad.tutor_name)
        else:
            raw_name = ad.tutor_name or CommonTexts.NO_NAME_PLACEHOLDER

        tutor_name = escape(raw_name.strip())
        tutor_subject = translate(escape(ad.tutor_subject or ""))
        tutor_type = translate(escape(ad.tutor_teaching_type or ""))
        tutor_format = translate(escape(ad.tutor_classes_format or ""))
        tutor_experience = escape(
            ad.tutor_experience or CommonTexts.NO_NAME_PLACEHOLDER
        )
        tutor_description = escape(
            ad.tutor_description or CommonTexts.NO_NAME_PLACEHOLDER
        )

        body_text = CommonTexts.AD_TEMPLATE.format(
            tutor_name=tutor_name,
            tutor_subject=tutor_subject,
            tutor_type=tutor_type,
            tutor_experience=tutor_experience,
            tutor_format=tutor_format,
            tutor_price=ad.tutor_price or 0,
            tutor_description=tutor_description,
        )

    statistic = (
        CommonTexts.STATISTICS_TEMPLATE.format(
            views=ad.views,
            likes=ad.likes,
        )
        if show_statistic
        else ""
    )

    if show_state:
        state_str = CommonTexts.BUTTON_TRANSLATIONS.get(ad.state, ad.state).upper()
        if show_publication_end and ad.state == "published" and ad.publishing_end:
            publishing_end = _display_date(ad.publishing_end)
            if publishing_end:
                state_str = CommonTexts.PUBLISHED_UNTIL_TEMPLATE.format(
                    publishing_end=publishing_end
                )
        state_header = CommonTexts.STATUS_HEADER_TEMPLATE.format(
            status=escape(state_str)
        )
    else:
        state_header = ""

    return f"{state_header}{body_text}{statistic}"


async def show_ad(
    target: Message,
    ad: TutorAd,
    keyboard: InlineKeyboardMarkup | None = None,
    show_state: bool = False,
    show_statistic: bool = False,
    show_publication_end: bool = False,
) -> list[int]:
    photos = ad.tutor_photo
    full_html = render_message(
        ad,
        show_state=show_state,
        show_statistic=show_statistic,
        show_publication_end=show_publication_end,
    )

    messages = []
    text = (
        full_html
        if len(full_html) <= TEXT_LIMIT
        else full_html[: TEXT_LIMIT - 3] + "..."
    )

    if photos:
        m_photo = await target.answer_media_group(
            media=[InputMediaPhoto(media=photo) for photo in photos],
        )
        for photo in m_photo:
            messages.append(photo.message_id)

    m = await target.answer(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    messages.append(m.message_id)

    return messages


def _display_date(value: str) -> str | None:
    try:
        parsed = date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None
    return parsed.strftime("%d.%m.%Y")
