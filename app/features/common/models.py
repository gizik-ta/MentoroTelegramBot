from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class Notification:
    notification_id: int
    user_id: int
    notification_text: str
    is_read: bool = False


@dataclass
class TutorAd:
    ad_id: Optional[int] = None
    user_id: Optional[int] = None
    tutor_name: Optional[Union[List[str], str]] = None
    tutor_photo: List[str] = field(default_factory=list)
    tutor_subject: Optional[str] = None
    tutor_teaching_type: Optional[str] = None
    tutor_experience: Optional[str] = None
    tutor_classes_format: Optional[str] = None
    tutor_description: Optional[str] = None
    tutor_price: Optional[int] = None
    finished: bool = False
    tutor_username: Optional[str] = None
    views: int = 0
    likes: int = 0
    state: Optional[str] = "payment_waiting"
    is_bought: bool = False
    bought_time: Optional[str] = None
    publishing_end: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "TutorAd":
        return cls(
            ad_id=data.get("ad_id"),
            user_id=data.get("user_id"),
            tutor_name=data.get("tutor_name"),
            tutor_photo=data.get("tutor_photo") or [],
            tutor_subject=data.get("tutor_subject"),
            tutor_teaching_type=data.get("tutor_teaching_type"),
            tutor_experience=data.get("tutor_experience"),
            tutor_classes_format=data.get("tutor_classes_format"),
            tutor_description=data.get("tutor_description"),
            tutor_price=data.get("tutor_price"),
            finished=data.get("finished", True),
            tutor_username=data.get("tutor_username"),
            views=data.get("views", 0),
            likes=data.get("likes", 0),
            state=data.get("state", "payment_waiting"),
            is_bought=data.get("is_bought", False),
            bought_time=data.get("bought_time"),
            publishing_end=data.get("publishing_end"),
        )

    @classmethod
    def build_ad(cls, data: dict) -> "TutorAd":
        """Build an ad from FSM data without coupling handlers to database rows."""

        return cls.from_dict(data)
