from urllib.parse import urlencode


class PaymentManager:
    @staticmethod
    def generate_yoomoney_link(
        wallet: str,
        amount: int,
        order_id: str,
        description: str,
    ) -> str:
        base_url = "https://yoomoney.ru/quickpay/confirm.xml"
        params = {
            "receiver": wallet,
            "quickpay-form": "button",
            "targets": description,
            "sum": amount,
            "label": order_id,
            "successURL": "https://t.me/repetitor_mentoro_bot",
        }
        return f"{base_url}?{urlencode(params)}"
