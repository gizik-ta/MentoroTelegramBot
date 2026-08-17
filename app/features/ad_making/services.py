from features.common.models import TutorAd


class AdMakingServices:
    EDITABLE_FIELDS = (
        "tutor_name",
        "tutor_photo",
        "tutor_subject",
        "tutor_teaching_type",
        "tutor_experience",
        "tutor_classes_format",
        "tutor_description",
        "tutor_price",
    )

    @staticmethod
    def build_ad(data: dict) -> TutorAd:
        return TutorAd(
            ad_id=data.get("ad_id"),
            tutor_name=data.get("tutor_name"),
            tutor_photo=data.get("tutor_photo") or [],
            tutor_subject=data.get("tutor_subject"),
            tutor_teaching_type=data.get("tutor_teaching_type"),
            tutor_experience=data.get("tutor_experience"),
            tutor_classes_format=data.get("tutor_classes_format"),
            tutor_description=data.get("tutor_description"),
            tutor_price=data.get("tutor_price"),
            finished=True,
            tutor_username=data.get("tutor_username"),
            views=data.get("views", 0),
            likes=data.get("likes", 0),
            state=data.get("state", "payment_waiting"),
            is_bought=data.get("is_bought", False),
            bought_time=data.get("bought_time"),
            publishing_end=data.get("publishing_end"),
        )

    @classmethod
    def edit_data(cls, ad: TutorAd) -> dict:
        data = {
            "ad_id": ad.ad_id,
            "tutor_name": ad.tutor_name,
            "tutor_photo": ad.tutor_photo or [],
            "tutor_subject": ad.tutor_subject,
            "tutor_teaching_type": ad.tutor_teaching_type,
            "tutor_experience": ad.tutor_experience,
            "tutor_classes_format": ad.tutor_classes_format,
            "tutor_description": ad.tutor_description,
            "tutor_price": ad.tutor_price,
            "tutor_username": ad.tutor_username,
            "views": ad.views,
            "likes": ad.likes,
            "state": ad.state,
            "is_bought": ad.is_bought,
            "bought_time": ad.bought_time,
            "publishing_end": ad.publishing_end,
            "update_ad": True,
            "is_changing": False,
        }
        data["original_editable_fields"] = cls._editable_values(data)
        return data

    @classmethod
    def has_information_changes(cls, data: dict) -> bool:
        original = data.get("original_editable_fields")
        if original is None:
            return True
        return cls._editable_values(data) != original

    @classmethod
    def _editable_values(cls, data: dict) -> dict:
        values = {field: data.get(field) for field in cls.EDITABLE_FIELDS}
        values["tutor_name"] = list(values.get("tutor_name") or [])
        values["tutor_photo"] = list(values.get("tutor_photo") or [])
        return values

    @staticmethod
    def prepare_updated_ad(ad: TutorAd) -> TutorAd:
        """Return edited existing content to moderation when payment is not needed."""

        if ad.is_bought or ad.state in {"published", "rejected", "on_check"}:
            ad.state = "on_check"
        return ad
