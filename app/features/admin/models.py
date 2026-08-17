from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubscriptionDistribution:
    months: int
    ads_count: int
    percentage: float


@dataclass(frozen=True)
class AdminStatistics:
    active_users_total: int = 0
    active_users_30_days: int = 0
    active_users_7_days: int = 0
    actions_30_days: int = 0
    errors_30_days: int = 0
    average_processing_ms_30_days: float = 0.0
    tutors_total: int = 0
    ads_total: int = 0
    ads_published: int = 0
    ads_on_check: int = 0
    ads_rejected: int = 0
    views_total: int = 0
    unique_viewers: int = 0
    saves_total: int = 0
    paying_tutors: int = 0
    paid_ads: int = 0
    paid_orders: int = 0
    paid_orders_30_days: int = 0
    paid_orders_6_months: int = 0
    revenue_30_days: int = 0
    revenue_6_months: int = 0
    revenue_all_time: int = 0
    average_purchased_months: float = 0.0
    subscription_distribution: list[SubscriptionDistribution] = field(
        default_factory=list
    )
