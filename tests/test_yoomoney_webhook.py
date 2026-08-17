import asyncio
import sqlite3

from features.my_ads.payment_redirect import create_payment_redirect_app
from features.payments.yoomoney_webhook import calculate_yoomoney_sign
from infrastructure.database.connection import DatabaseConnection
from infrastructure.database.schema import init_db

SECRET = "test-secret"


def _signed_notification(**overrides: str) -> dict[str, str]:
    payload = {
        "notification_type": "p2p-incoming",
        "operation_id": "provider-operation-1",
        "amount": "198.00",
        "withdraw_amount": "200.00",
        "currency": "643",
        "datetime": "2026-08-18T10:00:00Z",
        "sender": "",
        "codepro": "false",
        "label": "order-1",
        "unaccepted": "false",
    }
    payload.update(overrides)
    payload["sign"] = calculate_yoomoney_sign(list(payload.items()), SECRET)
    return payload


def _seed_payment_database(db_path) -> None:
    async def seed() -> None:
        database = DatabaseConnection(str(db_path))
        await database.connect()
        await init_db(database)
        await database.conn.execute("INSERT INTO users (user_id) VALUES (10)")
        await database.conn.execute(
            """
            INSERT INTO ads (ad_id, user_id, finished, state, is_bought)
            VALUES (1, 10, TRUE, 'payment_waiting', FALSE)
            """
        )
        await database.conn.execute(
            """
            INSERT INTO transactions (
                uuid, user_id, ad_id, item_id, status, created_at,
                amount_rub, order_kind
            ) VALUES (
                'order-1', 10, 1, 1, 'pending',
                '2026-08-18T09:00:00Z', 200, 'initial'
            )
            """
        )
        await database.conn.commit()
        await database.disconnect()

    asyncio.run(seed())


def _create_client(db_path):
    app = create_payment_redirect_app(
        str(db_path),
        "telegram-test-token",
        yoomoney_secret=SECRET,
    )
    return app.test_client()


def test_valid_callback_marks_transaction_paid_and_buys_ad(tmp_path):
    db_path = tmp_path / "valid-payment.db"
    _seed_payment_database(db_path)

    response = _create_client(db_path).post(
        "/yoomoney_webhook",
        data=_signed_notification(),
    )

    assert response.status_code == 200
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        transaction = dict(
            connection.execute(
                """
                SELECT status, provider_operation_id, gross_amount,
                       net_amount, notification_type
                FROM transactions WHERE uuid = 'order-1'
                """
            ).fetchone()
        )
        ad = dict(
            connection.execute(
                """
                SELECT is_bought, bought_time, publishing_end, state
                FROM ads WHERE ad_id = 1
                """
            ).fetchone()
        )
        callback = dict(
            connection.execute(
                """
                SELECT status, result_code
                FROM yoomoney_callbacks
                WHERE operation_id = 'provider-operation-1'
                """
            ).fetchone()
        )

    assert transaction == {
        "status": "paid",
        "provider_operation_id": "provider-operation-1",
        "gross_amount": "200.00",
        "net_amount": "198.00",
        "notification_type": "p2p-incoming",
    }
    assert ad == {
        "is_bought": 1,
        "bought_time": "2026-08-18",
        "publishing_end": "2026-09-17",
        "state": "on_check",
    }
    assert callback == {"status": "accepted", "result_code": "accepted"}


def test_callback_replay_and_second_operation_do_not_extend_ad_twice(tmp_path):
    db_path = tmp_path / "idempotent-payment.db"
    _seed_payment_database(db_path)
    client = _create_client(db_path)

    first = client.post("/yoomoney_webhook", data=_signed_notification())
    replay = client.post("/yoomoney_webhook", data=_signed_notification())
    second_operation = client.post(
        "/yoomoney_webhook",
        data=_signed_notification(operation_id="provider-operation-2"),
    )

    assert first.status_code == replay.status_code == second_operation.status_code == 200
    with sqlite3.connect(db_path) as connection:
        transaction = connection.execute(
            """
            SELECT provider_operation_id FROM transactions WHERE uuid = 'order-1'
            """
        ).fetchone()[0]
        publication_end = connection.execute(
            "SELECT publishing_end FROM ads WHERE ad_id = 1"
        ).fetchone()[0]
        callbacks = connection.execute(
            """
            SELECT operation_id, status, result_code
            FROM yoomoney_callbacks
            ORDER BY operation_id
            """
        ).fetchall()

    assert transaction == "provider-operation-1"
    assert publication_end == "2026-09-17"
    assert callbacks == [
        ("provider-operation-1", "accepted", "accepted"),
        (
            "provider-operation-2",
            "anomaly",
            "already_paid_second_operation",
        ),
    ]


def test_invalid_signature_and_amount_do_not_mutate_business_state(tmp_path):
    db_path = tmp_path / "rejected-payment.db"
    _seed_payment_database(db_path)
    client = _create_client(db_path)

    bad_signature = _signed_notification()
    bad_signature["sign"] = "0" * 64
    signature_response = client.post(
        "/yoomoney_webhook",
        data=bad_signature,
    )
    amount_response = client.post(
        "/yoomoney_webhook",
        data=_signed_notification(withdraw_amount="199.00"),
    )

    assert signature_response.status_code == 400
    assert amount_response.status_code == 200
    with sqlite3.connect(db_path) as connection:
        transaction_status = connection.execute(
            "SELECT status FROM transactions WHERE uuid = 'order-1'"
        ).fetchone()[0]
        ad_bought = connection.execute(
            "SELECT is_bought FROM ads WHERE ad_id = 1"
        ).fetchone()[0]
        callbacks = connection.execute(
            "SELECT status, result_code FROM yoomoney_callbacks"
        ).fetchall()

    assert transaction_status == "pending"
    assert ad_bought == 0
    assert callbacks == [("rejected", "amount_mismatch")]
