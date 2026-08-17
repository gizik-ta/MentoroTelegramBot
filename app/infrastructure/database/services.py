from datetime import date, datetime, timedelta, timezone

from features.common.models import TutorAd
from infrastructure.database.repositories.ad_repo import AdRepository
from infrastructure.database.repositories.free_trial_repo import FreeTrialRepository
from infrastructure.database.repositories.trans_repo import TransactionRepository


class AdService:
    def __init__(
        self,
        ad_repo: AdRepository,
        trans_repo: TransactionRepository,
        free_trial_repo: FreeTrialRepository,
    ):
        self.ad_repo = ad_repo
        self.trans_repo = trans_repo
        self.free_trial_repo = free_trial_repo

    @staticmethod
    def is_free_trial_eligible(username: str | None) -> bool:
        # return bool(username and username in TRIAL_USERS_IDS)
        return True

    async def ensure_free_trial_entitlement(
        self,
        user_id: int,
        username: str | None,
    ) -> bool:
        if not self.is_free_trial_eligible(username):
            return False
        return await self.free_trial_repo.ensure_entitlement(
            user_id,
            datetime.now(timezone.utc),
        )

    async def create_ad(self, user_id: int, user_ad: TutorAd) -> int:
        new_ad_id = await self.ad_repo.add_ad(user_id, user_ad)

        if self.is_free_trial_eligible(user_ad.tutor_username):
            activated_at = datetime.now(timezone.utc)
            await self.free_trial_repo.claim_and_activate(
                user_id=user_id,
                ad_id=new_ad_id,
                activated_at=activated_at,
                expires_at=activated_at + timedelta(days=30),
            )
        return new_ad_id

    async def activate_ad(
        self,
        uuid_str: str,
        bought_time: datetime,
    ) -> None:
        bought_str = bought_time.strftime("%Y-%m-%d")

        tx_data = await self.trans_repo.get_by_uuid(uuid_str)
        if not tx_data:
            return

        user_id, ad_id, order_kind = tx_data
        if order_kind == "renewal":
            ad = await self.ad_repo.get_by_id(ad_id)
            if ad is None or ad.user_id != user_id:
                return
            current_end = self._date_or_none(ad.publishing_end)
            base_date = (
                max(current_end, bought_time.date())
                if current_end
                else bought_time.date()
            )
            end_str = (base_date + timedelta(days=30)).isoformat()
            await self.trans_repo.mark_paid(uuid_str)
            await self.ad_repo.renew_ad(
                user_id,
                ad_id,
                bought_str,
                end_str,
            )
            return

        end_str = (bought_time + timedelta(days=30)).strftime("%Y-%m-%d")
        await self.trans_repo.mark_paid(uuid_str)
        await self.ad_repo.set_ad_bought(user_id, ad_id, bought_str, end_str)

    @staticmethod
    def _date_or_none(value: str | None) -> date | None:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
