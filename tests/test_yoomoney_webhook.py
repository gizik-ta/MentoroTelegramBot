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
        await database.conn.execute(
            """
            INSERT INTO payment_redirects (
                token, transaction_uuid, user_id, destination_url,
                ad_chat_id, ad_message_id
            ) VALUES (
                'redirect-token', 'order-1', 10,
                'https://yoomoney.ru/quickpay/confirm?label=order-1',
                100, 200
            )
            """
        )
        await database.conn.commit()
        await database.disconnect()

    asyncio.run(seed())


def _create_client(db_path, edits=None):
    edits = edits if edits is not None else []
    app = create_payment_redirect_app(
        str(db_path),
        "telegram-test-token",
        telegram_delete=lambda *_: True,
        telegram_edit=lambda chat_id, message_id, text, keyboard: edits.append(
            (chat_id, message_id, text, keyboard)
        )
        or True,
        yoomoney_secret=SECRET,
    )
    return app.test_client()


def test_valid_callback_marks_transaction_paid_and_buys_ad(tmp_path):
    db_path = tmp_path / "valid-payment.db"
    _seed_payment_database(db_path)
    edits = []

    response = _create_client(db_path, edits).post(
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
        notification = connection.execute(
            "SELECT notification_text FROM notifications WHERE user_id = 10"
        ).fetchone()[0]

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
    assert notification == "Оплата 200 ₽ получена. Объявление №1 обновлено."
    assert len(edits) == 1
    chat_id, message_id, text, keyboard = edits[0]
    assert (chat_id, message_id) == (100, 200)
    assert "НА ПРОВЕРКЕ" in text
    buttons = [button for row in keyboard["inline_keyboard"] for button in row]
    assert all(button["text"] != "ОПЛАТИТ ОБЪЯВЛЕНИЕ" for button in buttons)


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


def test_renewal_callback_refreshes_ad_with_new_end_date_and_renew_button(tmp_path):
    db_path = tmp_path / "renewal-payment.db"
    _seed_payment_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            UPDATE ads
            SET state = 'published', is_bought = TRUE,
                publishing_end = '2026-08-31'
            WHERE ad_id = 1
            """
        )
        connection.execute(
            "UPDATE transactions SET order_kind = 'renewal' WHERE uuid = 'order-1'"
        )
        connection.commit()
    edits = []

    response = _create_client(db_path, edits).post(
        "/yoomoney_webhook",
        data=_signed_notification(),
    )

    assert response.status_code == 200
    assert len(edits) == 1
    _, _, text, keyboard = edits[0]
    assert "ОПУБЛИКОВАНО ДО 30.09.2026" in text
    buttons = [button for row in keyboard["inline_keyboard"] for button in row]
    assert any(button["text"] == "Продлить публикацию" for button in buttons)


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
