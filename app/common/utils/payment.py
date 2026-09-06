from urllib.parse import urlencode


class PaymentManager:
    QUICKPAY_URL = "https://yoomoney.ru/quickpay/confirm"

    @staticmethod
    def generate_yoomoney_link(
        wallet: str,
        amount: int,
        order_id: str,
        description: str,
        payment_method: str = "AC",
    ) -> str:
        if payment_method not in {"AC", "PC"}:
            raise ValueError("Unsupported YooMoney payment method")

        params = {
            "receiver": wallet,
            "quickpay-form": "button",
            "paymentType": payment_method,
            "targets": description,
            "sum": amount,
            "label": order_id,
            "successURL": "https://t.me/repetitor_mentoro_bot",
        }
        return f"{PaymentManager.QUICKPAY_URL}?{urlencode(params)}"
