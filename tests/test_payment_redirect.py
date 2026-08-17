import asyncio
import sqlite3

from features.my_ads.payment_redirect import (
    PaymentRedirectServer,
    create_payment_redirect_app,
)
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.repositories.payment_redirect_repo import (
    PaymentRedirectRepository,
)
from infrastructure.database.repositories.trans_repo import TransactionRepository
from infrastructure.database.schema import init_db


def test_payment_redirect_deletes_message_and_opens_yoomoney(tmp_path):
    db_path = tmp_path / "payment-redirect.db"

    async def seed():
        db = DatabaseConnection(str(db_path))
        await db.connect()
        await init_db(db)
        await db.conn.execute("INSERT INTO users (user_id) VALUES (10)")
        await db.conn.execute(
            "INSERT INTO ads (user_id) VALUES (10)"
        )
        await db.conn.commit()
        transaction_repo = TransactionRepository(db)
        await transaction_repo.make_transaction(
            "order-id",
            10,
            1,
            1,
            "2026-08-17T10:00:00+00:00",
        )
        redirect_repo = PaymentRedirectRepository(db)
        await redirect_repo.create(
            "redirect-token",
            "order-id",
            10,
            "https://yoomoney.ru/quickpay/confirm.xml?label=order-id",
        )
        assert await redirect_repo.attach_message(
            "redirect-token",
            10,
            20,
            30,
        )
        await db.disconnect()

    asyncio.run(seed())
    deleted = []
    app = create_payment_redirect_app(
        str(db_path),
        "test-token",
        lambda chat_id, message_id: deleted.append((chat_id, message_id)) or True,
    )

    response = app.test_client().get("/payment/open/redirect-token")

    assert response.status_code == 302
    assert response.location.startswith("https://yoomoney.ru/quickpay/confirm.xml")
    assert deleted == [(20, 30)]
    with sqlite3.connect(db_path) as connection:
        opened_at = connection.execute(
            "SELECT opened_at FROM payment_redirects WHERE token = ?",
            ("redirect-token",),
        ).fetchone()[0]
    assert opened_at is not None


def test_payment_redirect_rejects_unknown_token(tmp_path):
    db_path = tmp_path / "empty.db"

    async def seed():
        db = DatabaseConnection(str(db_path))
        await db.connect()
        await init_db(db)
        await db.disconnect()

    asyncio.run(seed())
    app = create_payment_redirect_app(str(db_path), "test-token", lambda *_: True)

    assert app.test_client().get("/payment/open/unknown").status_code == 404


def test_payment_redirect_server_starts_and_stops(tmp_path):
    async def scenario():
        server = PaymentRedirectServer(
            db_path=str(tmp_path / "server.db"),
            bot_token="test-token",
            host="127.0.0.1",
            port=0,
        )
        await server.start()
        assert server._server is not None
        assert server._thread is not None and server._thread.is_alive()
        await server.stop()
        assert server._server is None
        assert server._thread is None

    asyncio.run(scenario())
