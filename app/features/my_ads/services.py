import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from common.data.items_to_sell import ITEMS
from common.utils.payment import PaymentManager
from configuration.config import config
from infrastructure.database import ad_repo, payment_redirect_repo, trans_repo

from .pricing import PRICING


@dataclass(frozen=True)
class PaymentSession:
    redirect_token: str
    redirect_url: str


class MyAdsServices:
    @staticmethod
    async def get_owned_ad(user_id: int, ad_id: int):
        ad = await ad_repo.get_by_id(ad_id)
        return ad if ad is not None and ad.user_id == user_id else None

    @staticmethod
    async def delete_owned_ad(user_id: int, ad_id: int) -> bool:
        return await ad_repo.delete_ad(ad_id=ad_id, user_id=user_id)

    @staticmethod
    async def owned_ad_is_bought(user_id: int, ad_id: int) -> bool:
        return await ad_repo.is_bought(ad_id=ad_id, user_id=user_id)

    @classmethod
    async def payment(
        cls,
        user_id: int,
        ad_id: int,
        payment_type: str,
        description: str,
        order_kind: str = "initial",
    ) -> PaymentSession:
        order_id = str(uuid.uuid4())
        redirect_token = str(uuid.uuid4())
        destination_url = cls.generate_yoomoney_link(
            payment_type,
            order_id,
            description,
        )

        created_at = datetime.now(timezone.utc).isoformat()

        await trans_repo.make_transaction(
            order_id,
            user_id,
            ad_id,
            ITEMS[payment_type],
            created_at,
            PRICING[payment_type],
            order_kind,
        )
        await payment_redirect_repo.create(
            token=redirect_token,
            transaction_uuid=order_id,
            user_id=user_id,
            destination_url=destination_url,
        )

        if not config.payment_redirect_base_url:
            raise RuntimeError("SERVER_IP or PAYMENT_REDIRECT_BASE_URL is required")
        return PaymentSession(
            redirect_token=redirect_token,
            redirect_url=(
                f"{config.payment_redirect_base_url}/payment/open/{redirect_token}"
            ),
        )

    @staticmethod
    async def attach_payment_message(
        token: str,
        user_id: int,
        chat_id: int,
        message_id: int,
    ) -> bool:
        return await payment_redirect_repo.attach_message(
            token,
            user_id,
            chat_id,
            message_id,
        )

    @staticmethod
    async def attach_ad_message(
        token: str,
        user_id: int,
        chat_id: int,
        message_id: int,
    ) -> bool:
        return await payment_redirect_repo.attach_ad_message(
            token,
            user_id,
            chat_id,
            message_id,
        )

    @staticmethod
    def generate_yoomoney_link(
        payment_type: str,
        order_id: str,
        description: str,
    ) -> str:
        return PaymentManager.generate_yoomoney_link(
            wallet=str(config.wallet_id),
            amount=PRICING[payment_type],
            order_id=order_id,
            description=description,
        )
