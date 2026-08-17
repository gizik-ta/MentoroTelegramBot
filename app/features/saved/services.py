from infrastructure.database import ad_repo


class SavedAdsServices:
    @staticmethod
    async def get_user_ads(user_id: int):
        return await ad_repo.get_liked_ads(user_id)

    @staticmethod
    async def set_saved(ad_id: int, user_id: int, is_saved: bool) -> None:
        if is_saved:
            await ad_repo.like_ad(ad_id, user_id)
        else:
            await ad_repo.unlike_ad(ad_id, user_id)

    @staticmethod
    async def get_contact_username(ad_id: int) -> str | None:
        ad = await ad_repo.get_by_id(ad_id)
        return ad.tutor_username if ad else None
