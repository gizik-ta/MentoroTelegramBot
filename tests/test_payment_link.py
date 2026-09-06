from urllib.parse import parse_qs, urlparse

import pytest
from common.utils.payment import PaymentManager


def test_yoomoney_quickpay_link_uses_current_card_form_parameters():
    link = PaymentManager.generate_yoomoney_link(
        wallet="410011234567890",
        amount=200,
        order_id="order-id",
        description="Оплата объявления",
    )

    parsed = urlparse(link)
    params = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.hostname == "yoomoney.ru"
    assert parsed.path == "/quickpay/confirm"
    assert params == {
        "receiver": ["410011234567890"],
        "quickpay-form": ["button"],
        "paymentType": ["AC"],
        "targets": ["Оплата объявления"],
        "sum": ["200"],
        "label": ["order-id"],
        "successURL": ["https://t.me/repetitor_mentoro_bot"],
    }


def test_yoomoney_quickpay_link_supports_wallet_payment():
    link = PaymentManager.generate_yoomoney_link(
        wallet="410011234567890",
        amount=200,
        order_id="order-id",
        description="Оплата объявления",
        payment_method="PC",
    )

    assert parse_qs(urlparse(link).query)["paymentType"] == ["PC"]


def test_yoomoney_quickpay_link_rejects_unknown_payment_method():
    with pytest.raises(ValueError, match="Unsupported YooMoney payment method"):
        PaymentManager.generate_yoomoney_link(
            wallet="410011234567890",
            amount=200,
            order_id="order-id",
            description="Оплата объявления",
            payment_method="cash",
        )
