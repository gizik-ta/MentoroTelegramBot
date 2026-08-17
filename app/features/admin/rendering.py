from html import escape

from aiogram.enums import ParseMode
from aiogram.types import Message, ReplyKeyboardMarkup
from features.common.models import TutorAd
from features.common.rendering import show_ad

from .keyboards import AdminKeyboards
from .models import AdminStatistics
from .texts import AdminTexts


class AdminRendering:
    @staticmethod
    def title() -> tuple[str, ReplyKeyboardMarkup]:
        return AdminTexts.TITLE, AdminKeyboards.menu()

    @staticmethod
    def moderation_title() -> tuple[str, ReplyKeyboardMarkup]:
        return AdminTexts.MODERATION_TITLE, AdminKeyboards.moderation_navigation()

    @staticmethod
    def statistics_title() -> tuple[str, ReplyKeyboardMarkup]:
        return AdminTexts.STATISTICS_TITLE, AdminKeyboards.moderation_navigation()

    @staticmethod
    def notifications_title() -> tuple[str, ReplyKeyboardMarkup]:
        return AdminTexts.NOTIFICATIONS_TITLE, AdminKeyboards.moderation_navigation()

    @staticmethod
    def warnings(warnings: list[dict]) -> list[str]:
        if not warnings:
            return [AdminTexts.NO_WARNINGS]
        return [str(warning.get("text") or "") for warning in warnings]

    @staticmethod
    def statistics(statistics: AdminStatistics) -> str:
        if statistics.subscription_distribution:
            rows = [AdminTexts.SUBSCRIPTION_DISTRIBUTION_HEADER]
            rows.extend(
                AdminTexts.SUBSCRIPTION_DISTRIBUTION_ROW.format(
                    months=item.months,
                    percentage=item.percentage,
                    ads_count=item.ads_count,
                )
                for item in statistics.subscription_distribution
            )
            distribution = "\n".join(rows)
        else:
            distribution = AdminTexts.NO_SUBSCRIPTION_DATA

        values = {
            **statistics.__dict__,
            "subscription_distribution": distribution,
            "revenue_30_days": AdminRendering._money(statistics.revenue_30_days),
            "revenue_6_months": AdminRendering._money(statistics.revenue_6_months),
            "revenue_all_time": AdminRendering._money(statistics.revenue_all_time),
        }
        return AdminTexts.STATISTICS_TEMPLATE.format(**values)

    @staticmethod
    def _money(amount: int) -> str:
        return f"{amount:,}".replace(",", " ")

    @staticmethod
    async def moderation_queue(target: Message, ads: list[TutorAd]) -> list[int]:
        if not ads:
            message = await target.answer(AdminTexts.NO_ADS_ON_CHECK)
            return [message.message_id]

        message_ids: list[int] = []
        for ad in ads:
            sent_ids = await show_ad(
                target,
                ad,
                AdminKeyboards.moderation_actions(ad.ad_id),
                show_state=True,
                show_statistic=False,
            )
            message_ids.extend(sent_ids)
        return message_ids

    @staticmethod
    async def rejection_prompt(target: Message, ad_id: int) -> int:
        message = await target.answer(
            AdminTexts.REJECTION_PROMPT,
            reply_markup=AdminKeyboards.rejection_actions(ad_id),
        )
        return message.message_id

    @staticmethod
    async def show_rejection_reason(
        target: Message,
        prompt_message_id: int,
        ad_id: int,
        reason: str,
    ) -> None:
        await target.bot.edit_message_text(
            chat_id=target.chat.id,
            message_id=prompt_message_id,
            text=AdminTexts.REJECTION_SAVED.format(reason=escape(reason)),
            reply_markup=AdminKeyboards.rejection_actions(ad_id),
            parse_mode=ParseMode.HTML,
        )
