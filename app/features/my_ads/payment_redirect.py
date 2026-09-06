import json
import sqlite3
import threading
from collections.abc import Callable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen

from features.payments import register_yoomoney_webhook
from flask import Flask, abort, redirect
from werkzeug.serving import BaseWSGIServer, make_server

TelegramDelete = Callable[[int, int], bool]


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
    yoomoney_secret: str = "",
) -> Flask:
    app = Flask(__name__)
    register_yoomoney_webhook(
        app,
        db_path=db_path,
        secret=yoomoney_secret,
    )
    delete_message = telegram_delete or (
        lambda chat_id, message_id: _telegram_delete(
            bot_token,
            chat_id,
            message_id,
        )
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
