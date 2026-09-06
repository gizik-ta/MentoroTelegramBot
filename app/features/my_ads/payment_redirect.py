import json
import sqlite3
import threading
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from features.common.keyboards import CommonKeyboards
from features.common.rendering import render_message
from features.payments import register_yoomoney_webhook
from flask import Flask, abort, redirect
from infrastructure.database.repositories.ad_repo import AdRepository
from werkzeug.serving import BaseWSGIServer, make_server

TelegramDelete = Callable[[int, int], bool]
TelegramEdit = Callable[[int, int, str, dict], bool]


def _telegram_delete(bot_token: str, chat_id: int, message_id: int) -> bool:
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/deleteMessage",
        data=urlencode(
            {"chat_id": str(chat_id), "message_id": str(message_id)}
        ).encode(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
    except (OSError, TimeoutError, ValueError):
        return False
    return result.get("ok") is True


def _telegram_edit(
    bot_token: str,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: dict,
) -> bool:
    request = Request(
        f"https://api.telegram.org/bot{bot_token}/editMessageText",
        data=json.dumps(
            {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup,
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read())
    except (OSError, TimeoutError, ValueError):
        return False
    return result.get("ok") is True


def _refresh_paid_ad_message(
    db_path: str,
    user_id: int,
    ad_id: int,
    delete_message: TelegramDelete,
    edit_message: TelegramEdit,
) -> bool:
    with sqlite3.connect(db_path, timeout=20) as connection:
        connection.row_factory = sqlite3.Row
        message = connection.execute(
            """
            SELECT payment_redirects.chat_id, payment_redirects.message_id,
                   payment_redirects.ad_chat_id, payment_redirects.ad_message_id
            FROM payment_redirects
            JOIN transactions
              ON transactions.uuid = payment_redirects.transaction_uuid
            WHERE transactions.user_id = ?
              AND transactions.ad_id = ?
              AND transactions.status = 'paid'
              AND payment_redirects.ad_chat_id IS NOT NULL
              AND payment_redirects.ad_message_id IS NOT NULL
            ORDER BY transactions.paid_at DESC, payment_redirects.created_at DESC
            LIMIT 1
            """,
            (user_id, ad_id),
        ).fetchone()
        ad_row = connection.execute(
            "SELECT * FROM ads WHERE ad_id = ? AND user_id = ?",
            (ad_id, user_id),
        ).fetchone()

    if message is None or ad_row is None:
        return False

    if message["chat_id"] is not None and message["message_id"] is not None:
        delete_message(int(message["chat_id"]), int(message["message_id"]))

    ad = AdRepository.row_to_ad(ad_row)
    text = render_message(ad, show_state=True, show_publication_end=True)
    keyboard = CommonKeyboards.owner_ad_actions(
        ad_id,
        ad.is_bought,
        ad.state,
    ).model_dump(mode="json", exclude_none=True)
    return edit_message(
        int(message["ad_chat_id"]),
        int(message["ad_message_id"]),
        text,
        keyboard,
    )


def _is_yoomoney_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname in {"yoomoney.ru", "www.yoomoney.ru"}
        and parsed.port in {None, 443}
        and parsed.path in {"/quickpay/confirm", "/quickpay/confirm.xml"}
    )


def _normalize_yoomoney_url(url: str) -> str | None:
    if not _is_yoomoney_url(url):
        return None

    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if not any(name == "paymentType" for name, _ in params):
        params.append(("paymentType", "AC"))

    return urlunparse(
        parsed._replace(
            path="/quickpay/confirm",
            query=urlencode(params),
            fragment="",
        )
    )


def create_payment_redirect_app(
    db_path: str,
    bot_token: str,
    telegram_delete: TelegramDelete | None = None,
    telegram_edit: TelegramEdit | None = None,
    yoomoney_secret: str = "",
) -> Flask:
    app = Flask(__name__)
    delete_message = telegram_delete or (
        lambda chat_id, message_id: _telegram_delete(
            bot_token,
            chat_id,
            message_id,
        )
    )
    edit_message = telegram_edit or (
        lambda chat_id, message_id, text, reply_markup: _telegram_edit(
            bot_token,
            chat_id,
            message_id,
            text,
            reply_markup,
        )
    )
    register_yoomoney_webhook(
        app,
        db_path=db_path,
        secret=yoomoney_secret,
        on_payment_accepted=lambda user_id, ad_id: _refresh_paid_ad_message(
            db_path,
            user_id,
            ad_id,
            delete_message,
            edit_message,
        ),
    )

    @app.get("/payment/open/<token>")
    def open_payment(token: str):
        with sqlite3.connect(db_path, timeout=20) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT destination_url, chat_id, message_id, opened_at
                FROM payment_redirects
                WHERE token = ?
                """,
                (token,),
            ).fetchone()
            if row is None:
                abort(404)

            destination_url = _normalize_yoomoney_url(str(row["destination_url"]))
            if destination_url is None:
                abort(400)

            if (
                row["opened_at"] is None
                and row["chat_id"] is not None
                and row["message_id"] is not None
                and delete_message(int(row["chat_id"]), int(row["message_id"]))
            ):
                connection.execute(
                    """
                    UPDATE payment_redirects
                    SET opened_at = CURRENT_TIMESTAMP
                    WHERE token = ? AND opened_at IS NULL
                    """,
                    (token,),
                )
                connection.commit()

        return redirect(destination_url, code=302)

    return app


class PaymentRedirectServer:
    def __init__(
        self,
        db_path: str,
        bot_token: str,
        host: str,
        port: int,
        yoomoney_secret: str = "",
    ) -> None:
        self.app = create_payment_redirect_app(
            db_path,
            bot_token,
            yoomoney_secret=yoomoney_secret,
        )
        self.host = host
        self.port = port
        self._server: BaseWSGIServer | None = None
        self._thread: threading.Thread | None = None

    async def start(self) -> None:
        if self._server is not None:
            return
        self._server = make_server(self.host, self.port, self.app, threaded=True)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="mentoro-payment-api",
            daemon=True,
        )
        self._thread.start()

    async def stop(self) -> None:
        if self._server is None:
            return
        self._server.shutdown()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._server.server_close()
        self._server = None
        self._thread = None
