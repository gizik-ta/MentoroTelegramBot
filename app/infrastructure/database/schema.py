import json

from common.data.free_trial_users_id import TRIAL_USERS_IDS
from common.data.message_templates import DEFAULT_MESSAGE_TEMPLATES
from infrastructure.database.connection import DatabaseConnection


async def init_db(db: DatabaseConnection) -> None:
    """Creates tables if they do not exist."""
    async with db.conn.cursor() as cursor:
        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                title_message_id INTEGER,
                greeting_message_id INTEGER
            )
            """
        )

        await cursor.execute("PRAGMA table_info(users)")
        user_columns = {row[1] for row in await cursor.fetchall()}
        if "title_message_id" not in user_columns:
            await cursor.execute("ALTER TABLE users ADD COLUMN title_message_id INTEGER")
        if "greeting_message_id" not in user_columns:
            await cursor.execute(
                "ALTER TABLE users ADD COLUMN greeting_message_id INTEGER"
            )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS ads (
                ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT,
                photo TEXT DEFAULT '[]',
                subject TEXT,
                teaching_type TEXT,
                experience TEXT,
                classes_format TEXT,
                description TEXT,
                price INTEGER,
                finished BOOLEAN DEFAULT FALSE,
                tutor_username TEXT,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                state TEXT DEFAULT 'payment_waiting',
                is_bought BOOLEAN DEFAULT FALSE,
                bought_time TEXT,
                publishing_end TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute("PRAGMA table_info(ads)")
        columns = {row[1] for row in await cursor.fetchall()}
        if "rate" in columns:
            await cursor.execute("ALTER TABLE ads DROP COLUMN rate")

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_likes (
                user_id INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, ad_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(ad_id) REFERENCES ads(ad_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_views (
                user_id INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, ad_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(ad_id) REFERENCES ads(ad_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                uuid TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                ad_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                amount_rub INTEGER NOT NULL DEFAULT 200,
                paid_at TEXT,
                order_kind TEXT NOT NULL DEFAULT 'initial',
                provider_operation_id TEXT,
                gross_amount TEXT,
                net_amount TEXT,
                notification_type TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute("PRAGMA table_info(transactions)")
        transaction_columns = {row[1] for row in await cursor.fetchall()}
        if "amount_rub" not in transaction_columns:
            await cursor.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN amount_rub INTEGER NOT NULL DEFAULT 200"
            )
        if "paid_at" not in transaction_columns:
            await cursor.execute("ALTER TABLE transactions ADD COLUMN paid_at TEXT")
        if "order_kind" not in transaction_columns:
            await cursor.execute(
                "ALTER TABLE transactions "
                "ADD COLUMN order_kind TEXT NOT NULL DEFAULT 'initial'"
            )
        if "provider_operation_id" not in transaction_columns:
            await cursor.execute(
                "ALTER TABLE transactions ADD COLUMN provider_operation_id TEXT"
            )
        await cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_transactions_provider_operation_id "
            "ON transactions(provider_operation_id)"
        )
        if "gross_amount" not in transaction_columns:
            await cursor.execute(
                "ALTER TABLE transactions ADD COLUMN gross_amount TEXT"
            )
        if "net_amount" not in transaction_columns:
            await cursor.execute("ALTER TABLE transactions ADD COLUMN net_amount TEXT")
        if "notification_type" not in transaction_columns:
            await cursor.execute(
                "ALTER TABLE transactions ADD COLUMN notification_type TEXT"
            )
        await cursor.execute(
            """
            UPDATE transactions
            SET paid_at = created_at
            WHERE status = 'paid' AND paid_at IS NULL
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                notification_text TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_redirects (
                token TEXT PRIMARY KEY,
                transaction_uuid TEXT NOT NULL UNIQUE,
                user_id INTEGER NOT NULL,
                destination_url TEXT NOT NULL,
                chat_id INTEGER,
                message_id INTEGER,
                ad_chat_id INTEGER,
                ad_message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                opened_at TEXT,
                FOREIGN KEY(transaction_uuid)
                    REFERENCES transactions(uuid) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute("PRAGMA table_info(payment_redirects)")
        payment_redirect_columns = {row[1] for row in await cursor.fetchall()}
        if "ad_chat_id" not in payment_redirect_columns:
            await cursor.execute(
                "ALTER TABLE payment_redirects ADD COLUMN ad_chat_id INTEGER"
            )
        if "ad_message_id" not in payment_redirect_columns:
            await cursor.execute(
                "ALTER TABLE payment_redirects ADD COLUMN ad_message_id INTEGER"
            )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS yoomoney_callbacks (
                operation_id TEXT PRIMARY KEY,
                transaction_uuid TEXT,
                payload_digest TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                gross_amount TEXT NOT NULL,
                net_amount TEXT NOT NULL,
                currency TEXT NOT NULL,
                status TEXT NOT NULL CHECK (
                    status IN ('accepted', 'ignored', 'rejected', 'anomaly')
                ),
                result_code TEXT NOT NULL,
                received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(transaction_uuid)
                    REFERENCES transactions(uuid) ON DELETE SET NULL
            )
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS publication_reminders (
                ad_id INTEGER NOT NULL,
                reminder_date TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ad_id, reminder_date),
                FOREIGN KEY(ad_id) REFERENCES ads(ad_id) ON DELETE CASCADE
            )
            """
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS message_templates (
                template_key TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                template_text TEXT NOT NULL,
                parameters_json TEXT NOT NULL DEFAULT '[]',
                description TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await cursor.executemany(
            """
            INSERT INTO message_templates (
                template_key,
                category,
                template_text,
                parameters_json,
                description
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(template_key) DO UPDATE SET
                category = excluded.category,
                template_text = excluded.template_text,
                parameters_json = excluded.parameters_json,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP
            """,
            [
                (key, category, text, json.dumps(parameters), description)
                for key, category, text, parameters, description in DEFAULT_MESSAGE_TEMPLATES
            ],
        )

        await cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS free_trial_entitlements (
                user_id INTEGER PRIMARY KEY,
                ad_id INTEGER UNIQUE,
                notified_at TEXT NOT NULL,
                consumed_at TEXT,
                activated_at TEXT,
                expires_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY(ad_id) REFERENCES ads(ad_id) ON DELETE SET NULL
            )
            """
        )

        if TRIAL_USERS_IDS:
            placeholders = ", ".join("?" for _ in TRIAL_USERS_IDS)
            await cursor.execute(
                f"""
                INSERT OR IGNORE INTO free_trial_entitlements (
                    user_id,
                    ad_id,
                    notified_at,
                    consumed_at,
                    activated_at,
                    expires_at
                )
                SELECT
                    ads.user_id,
                    ads.ad_id,
                    COALESCE(ads.bought_time, CURRENT_TIMESTAMP),
                    COALESCE(ads.bought_time, CURRENT_TIMESTAMP),
                    COALESCE(ads.bought_time, CURRENT_TIMESTAMP),
                    ads.publishing_end
                FROM ads
                WHERE ads.tutor_username IN ({placeholders})
                  AND ads.is_bought = TRUE
                  AND ads.ad_id = (
                      SELECT MIN(first_trial.ad_id)
                      FROM ads AS first_trial
                      WHERE first_trial.user_id = ads.user_id
                        AND first_trial.tutor_username IN ({placeholders})
                        AND first_trial.is_bought = TRUE
                        AND NOT EXISTS (
                            SELECT 1
                            FROM transactions
                            WHERE transactions.ad_id = first_trial.ad_id
                              AND transactions.status = 'paid'
                        )
                  )
                  AND NOT EXISTS (
                      SELECT 1
                      FROM transactions
                      WHERE transactions.ad_id = ads.ad_id
                        AND transactions.status = 'paid'
                  )
                """,
                (*TRIAL_USERS_IDS, *TRIAL_USERS_IDS),
            )

        await db.conn.commit()
