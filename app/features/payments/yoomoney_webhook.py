import hashlib
import hmac
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, urlencode

from flask import Flask, request

ALLOWED_NOTIFICATION_TYPES = {"p2p-incoming", "card-incoming"}
FALSE_VALUES = {"false", "0", ""}


def canonical_notification(parameters: list[tuple[str, str]]) -> str:
    unsigned = [(key, value) for key, value in parameters if key != "sign"]
    unsigned.sort(key=lambda item: item[0])
    return urlencode(unsigned, doseq=True, quote_via=quote, safe="~")


def calculate_yoomoney_sign(
    parameters: list[tuple[str, str]],
    secret: str,
) -> str:
    canonical = canonical_notification(parameters)
    return hmac.new(
        secret.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_yoomoney_sign(
    parameters: list[tuple[str, str]],
    secret: str,
) -> bool:
    supplied_sign = next(
        (value for key, value in parameters if key == "sign"),
        "",
    )
    if not supplied_sign or not secret:
        return False
    expected_sign = calculate_yoomoney_sign(parameters, secret)
    return hmac.compare_digest(expected_sign, supplied_sign.lower())


def _decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _payment_date(value: str) -> date:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).date()
    except (AttributeError, ValueError):
        return datetime.now(timezone.utc).date()


def _payload_digest(parameters: list[tuple[str, str]]) -> str:
    return hashlib.sha256(
        canonical_notification(parameters).encode("utf-8")
    ).hexdigest()


def _record_callback(
    connection: sqlite3.Connection,
    *,
    operation_id: str,
    transaction_uuid: str | None,
    payload_digest: str,
    notification_type: str,
    gross_amount: str,
    net_amount: str,
    currency: str,
    status: str,
    result_code: str,
) -> None:
    connection.execute(
        """
        INSERT INTO yoomoney_callbacks (
            operation_id,
            transaction_uuid,
            payload_digest,
            notification_type,
            gross_amount,
            net_amount,
            currency,
            status,
            result_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            operation_id,
            transaction_uuid,
            payload_digest,
            notification_type,
            gross_amount,
            net_amount,
            currency,
            status,
            result_code,
        ),
    )


def _activate_ad(
    connection: sqlite3.Connection,
    *,
    transaction: sqlite3.Row,
    operation_id: str,
    notification_type: str,
    gross_amount: str,
    net_amount: str,
    paid_on: date,
) -> bool:
    user_id = int(transaction["user_id"])
    ad_id = int(transaction["ad_id"])
    order_kind = str(transaction["order_kind"])
    ad = connection.execute(
        """
        SELECT user_id, publishing_end
        FROM ads
        WHERE ad_id = ? AND user_id = ?
        """,
        (ad_id, user_id),
    ).fetchone()
    if ad is None:
        return False

    bought_str = paid_on.isoformat()
    if order_kind == "renewal":
        try:
            current_end = date.fromisoformat(str(ad["publishing_end"])[:10])
        except (TypeError, ValueError):
            current_end = None
        base_date = max(current_end, paid_on) if current_end else paid_on
        publishing_end = (base_date + timedelta(days=30)).isoformat()
        target_state = "published"
    else:
        publishing_end = (paid_on + timedelta(days=30)).isoformat()
        target_state = "on_check"

    transaction_updated = connection.execute(
        """
        UPDATE transactions
        SET status = 'paid',
            paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP),
            provider_operation_id = ?,
            gross_amount = ?,
            net_amount = ?,
            notification_type = ?
        WHERE uuid = ? AND status = 'pending'
        """,
        (
            operation_id,
            gross_amount,
            net_amount,
            notification_type,
            transaction["uuid"],
        ),
    )
    if transaction_updated.rowcount != 1:
        return False

    ad_updated = connection.execute(
        """
        UPDATE ads
        SET is_bought = TRUE,
            bought_time = ?,
            publishing_end = ?,
            state = ?
        WHERE ad_id = ? AND user_id = ?
        """,
        (bought_str, publishing_end, target_state, ad_id, user_id),
    )
    return ad_updated.rowcount == 1


def register_yoomoney_webhook(
    app: Flask,
    *,
    db_path: str,
    secret: str,
) -> None:
    @app.post("/yoomoney_webhook")
    def yoomoney_webhook():
        parameters = [(key, value) for key, value in request.form.items(multi=True)]
        if not verify_yoomoney_sign(parameters, secret):
            return "INVALID SIGNATURE", 400

        values = request.form
        operation_id = values.get("operation_id", "").strip()
        label = values.get("label", "").strip()
        notification_type = values.get("notification_type", "").strip()
        gross_amount_text = values.get("withdraw_amount", "").strip()
        net_amount_text = values.get("amount", "").strip()
        currency = values.get("currency", "").strip()
        digest = _payload_digest(parameters)

        if not operation_id:
            return "INVALID NOTIFICATION", 400

        with sqlite3.connect(db_path, timeout=20) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 20000")
            connection.execute("BEGIN IMMEDIATE")

            existing = connection.execute(
                """
                SELECT payload_digest
                FROM yoomoney_callbacks
                WHERE operation_id = ?
                """,
                (operation_id,),
            ).fetchone()
            if existing is not None:
                connection.commit()
                return "OK" if existing["payload_digest"] == digest else "IGNORED", 200

            transaction = connection.execute(
                """
                SELECT uuid, user_id, ad_id, status, amount_rub, order_kind
                FROM transactions
                WHERE uuid = ?
                """,
                (label,),
            ).fetchone()

            result_code = "accepted"
            callback_status = "accepted"
            gross_amount = _decimal(gross_amount_text)
            net_amount = _decimal(net_amount_text)

            if transaction is None:
                result_code = "unknown_order"
                callback_status = "rejected"
            elif notification_type not in ALLOWED_NOTIFICATION_TYPES:
                result_code = "notification_type"
                callback_status = "rejected"
            elif currency != "643":
                result_code = "currency"
                callback_status = "rejected"
            elif gross_amount is None or net_amount is None:
                result_code = "amount_format"
                callback_status = "rejected"
            elif gross_amount != Decimal(str(transaction["amount_rub"])):
                result_code = "amount_mismatch"
                callback_status = "rejected"
            elif values.get("unaccepted", "false").lower() not in FALSE_VALUES:
                result_code = "unaccepted"
                callback_status = "ignored"
            elif values.get("codepro", "false").lower() not in FALSE_VALUES:
                result_code = "codepro"
                callback_status = "ignored"
            elif transaction["status"] == "paid":
                result_code = "already_paid_second_operation"
                callback_status = "anomaly"
            elif transaction["status"] != "pending":
                result_code = "invalid_transaction_status"
                callback_status = "rejected"
            else:
                connection.execute("SAVEPOINT ad_activation")
                activated = _activate_ad(
                    connection,
                    transaction=transaction,
                    operation_id=operation_id,
                    notification_type=notification_type,
                    gross_amount=f"{gross_amount:.2f}",
                    net_amount=f"{net_amount:.2f}",
                    paid_on=_payment_date(values.get("datetime", "")),
                )
                if activated:
                    connection.execute("RELEASE SAVEPOINT ad_activation")
                else:
                    connection.execute("ROLLBACK TO SAVEPOINT ad_activation")
                    connection.execute("RELEASE SAVEPOINT ad_activation")
                    result_code = "ad_ownership_or_state"
                    callback_status = "rejected"

            _record_callback(
                connection,
                operation_id=operation_id,
                transaction_uuid=transaction["uuid"] if transaction else None,
                payload_digest=digest,
                notification_type=notification_type,
                gross_amount=gross_amount_text,
                net_amount=net_amount_text,
                currency=currency,
                status=callback_status,
                result_code=result_code,
            )
            connection.commit()

        return "OK", 200
