import asyncio
import json
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

from common.utils.action_logging import user_action_logger
from configuration.config import config
from features.common.models import TutorAd
from infrastructure.database import admin_repo, notify_repo, statistics_repo

from .models import AdminStatistics, SubscriptionDistribution
from .texts import AdminTexts


class AdminViewServices:
    @staticmethod
    def is_admin(user_id: int) -> bool:
        return user_id in config.admin_ids

    @staticmethod
    async def unread_notifications(user_id: int) -> int:
        return await notify_repo.count_unread_messages(user_id)


class AdminModerationServices:
    @staticmethod
    async def get_ads_on_check() -> list[TutorAd]:
        return await admin_repo.get_on_check_ads()

    @staticmethod
    async def get_ad_on_check(ad_id: int) -> TutorAd | None:
        return await admin_repo.get_on_check_ad(ad_id)

    @staticmethod
    async def approve(ad_id: int) -> TutorAd | None:
        ad = await admin_repo.approve_ad(ad_id)
        if ad is not None:
            await notify_repo.send_notification(
                ad.user_id,
                AdminTexts.APPROVAL_NOTIFICATION,
            )
        return ad

    @staticmethod
    async def reject(ad_id: int, reason: str) -> TutorAd | None:
        clean_reason = reason.strip()
        if not clean_reason or len(clean_reason) > 1000:
            return None

        ad = await admin_repo.reject_ad(ad_id)
        if ad is not None:
            await notify_repo.send_notification(
                ad.user_id,
                AdminTexts.REJECTION_NOTIFICATION.format(reason=escape(clean_reason)),
            )
        return ad


class AdminStatisticsServices:
    @classmethod
    async def get_statistics(
        cls,
        log_path: Path | None = None,
        now: datetime | None = None,
        repository=None,
    ) -> AdminStatistics:
        effective_log_path = log_path or user_action_logger.log_path
        effective_now = now or datetime.now(timezone.utc)
        if effective_now.tzinfo is None:
            effective_now = effective_now.replace(tzinfo=timezone.utc)
        effective_repository = repository or statistics_repo

        database_snapshot, activity = await asyncio.gather(
            effective_repository.get_snapshot(),
            asyncio.to_thread(
                cls._read_activity_log,
                effective_log_path,
                effective_now,
            ),
        )

        paid_ads = int(database_snapshot.get("paid_ads") or 0)
        paid_orders = int(database_snapshot.get("paid_orders") or 0)
        distribution = [
            SubscriptionDistribution(
                months=int(item["purchased_months"]),
                ads_count=int(item["ads_count"]),
                percentage=(int(item["ads_count"]) / paid_ads * 100)
                if paid_ads
                else 0.0,
            )
            for item in database_snapshot.get("subscription_distribution", [])
        ]

        return AdminStatistics(
            **activity,
            tutors_total=int(database_snapshot.get("tutors_total") or 0),
            ads_total=int(database_snapshot.get("ads_total") or 0),
            ads_published=int(database_snapshot.get("ads_published") or 0),
            ads_on_check=int(database_snapshot.get("ads_on_check") or 0),
            ads_rejected=int(database_snapshot.get("ads_rejected") or 0),
            views_total=int(database_snapshot.get("views_total") or 0),
            unique_viewers=int(database_snapshot.get("unique_viewers") or 0),
            saves_total=int(database_snapshot.get("saves_total") or 0),
            paying_tutors=int(database_snapshot.get("paying_tutors") or 0),
            paid_ads=paid_ads,
            paid_orders=paid_orders,
            paid_orders_30_days=int(database_snapshot.get("paid_orders_30_days") or 0),
            paid_orders_6_months=int(
                database_snapshot.get("paid_orders_6_months") or 0
            ),
            revenue_30_days=int(database_snapshot.get("revenue_30_days") or 0),
            revenue_6_months=int(database_snapshot.get("revenue_6_months") or 0),
            revenue_all_time=int(database_snapshot.get("revenue_all_time") or 0),
            average_purchased_months=(paid_orders / paid_ads) if paid_ads else 0.0,
            subscription_distribution=distribution,
        )

    @staticmethod
    def _read_activity_log(log_path: Path, now: datetime) -> dict:
        all_users: set[int] = set()
        users_30_days: set[int] = set()
        users_7_days: set[int] = set()
        processing_times: list[float] = []
        actions_30_days = 0
        errors_30_days = 0
        since_30_days = now - timedelta(days=30)
        since_7_days = now - timedelta(days=7)

        if not log_path.exists():
            return {
                "active_users_total": 0,
                "active_users_30_days": 0,
                "active_users_7_days": 0,
                "actions_30_days": 0,
                "errors_30_days": 0,
                "average_processing_ms_30_days": 0.0,
            }

        try:
            with log_path.open("r", encoding="utf-8") as log_file:
                for line in log_file:
                    try:
                        action = json.loads(line)
                        user_id = action.get("user_id")
                        timestamp = datetime.fromisoformat(
                            str(action.get("timestamp_utc") or "").replace(
                                "Z", "+00:00"
                            )
                        )
                    except (json.JSONDecodeError, TypeError, ValueError):
                        continue

                    if (
                        not isinstance(user_id, int)
                        or user_id in config.admin_ids
                        or action.get("event_type") not in {"Message", "CallbackQuery"}
                    ):
                        continue
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)

                    all_users.add(user_id)
                    if timestamp >= since_30_days:
                        users_30_days.add(user_id)
                        actions_30_days += 1
                        if action.get("status_code") == "error":
                            errors_30_days += 1
                        processing_time = action.get("processing_time_ms")
                        if isinstance(processing_time, (int, float)):
                            processing_times.append(float(processing_time))
                    if timestamp >= since_7_days:
                        users_7_days.add(user_id)
        except OSError:
            return {
                "active_users_total": 0,
                "active_users_30_days": 0,
                "active_users_7_days": 0,
                "actions_30_days": 0,
                "errors_30_days": 0,
                "average_processing_ms_30_days": 0.0,
            }

        average_processing = (
            sum(processing_times) / len(processing_times) if processing_times else 0.0
        )
        return {
            "active_users_total": len(all_users),
            "active_users_30_days": len(users_30_days),
            "active_users_7_days": len(users_7_days),
            "actions_30_days": actions_30_days,
            "errors_30_days": errors_30_days,
            "average_processing_ms_30_days": average_processing,
        }


class AdminWarningServices:
    @staticmethod
    async def get_warnings() -> list[dict]:
        warnings = await asyncio.to_thread(user_action_logger.warning_history)
        return list(reversed(warnings))
