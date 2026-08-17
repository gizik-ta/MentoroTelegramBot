from infrastructure.database.connection import db_conn
from infrastructure.database.repositories.ad_repo import AdRepository
from infrastructure.database.repositories.admin_repo import AdminRepository
from infrastructure.database.repositories.free_trial_repo import FreeTrialRepository
from infrastructure.database.repositories.notify_repo import NotificationRepository
from infrastructure.database.repositories.payment_redirect_repo import (
    PaymentRedirectRepository,
)
from infrastructure.database.repositories.statistics_repo import (
    AdminStatisticsRepository,
)
from infrastructure.database.repositories.subscription_repo import (
    SubscriptionMaintenanceRepository,
)
from infrastructure.database.repositories.trans_repo import TransactionRepository
from infrastructure.database.repositories.user_repo import UserRepository
from infrastructure.database.schema import init_db
from infrastructure.database.services import AdService

user_repo = UserRepository(db_conn)
ad_repo = AdRepository(db_conn)
admin_repo = AdminRepository(db_conn)
trans_repo = TransactionRepository(db_conn)
notify_repo = NotificationRepository(db_conn)
payment_redirect_repo = PaymentRedirectRepository(db_conn)
statistics_repo = AdminStatisticsRepository(db_conn)
subscription_repo = SubscriptionMaintenanceRepository(db_conn)
free_trial_repo = FreeTrialRepository(db_conn)
ad_service = AdService(ad_repo, trans_repo, free_trial_repo)


async def setup_database():
    """Make connection to db + make tables."""
    await db_conn.connect()
    await init_db(db_conn)


async def shutdown_database():
    """Close connection to db."""
    await db_conn.disconnect()
