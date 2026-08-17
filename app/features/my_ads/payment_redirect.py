import json
import sqlite3
import threading
from collections.abc import Callable
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

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
    return parsed.scheme == "https" and parsed.hostname in {
        "yoomoney.ru",
        "www.yoomoney.ru",
    }


def create_payment_redirect_app(
    db_path: str,
    bot_token: str,
    telegram_delete: TelegramDelete | None = None,
) -> Flask:
    app = Flask(__name__)
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

            destination_url = str(row["destination_url"])
            if not _is_yoomoney_url(destination_url):
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
    ) -> None:
        self.app = create_payment_redirect_app(db_path, bot_token)
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
            name="pomogator-payment-redirect",
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
