import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_ADMIN_ID = 5110492323


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _positive_int_env(name: str, default: int) -> int:
    value = _int_env(name, default)
    return value if value > 0 else default


def _admin_ids() -> frozenset[int]:
    configured_ids = {DEFAULT_ADMIN_ID}
    for value in os.getenv("ADMIN_IDS", "").split(","):
        value = value.strip()
        if value:
            try:
                configured_ids.add(int(value))
            except ValueError:
                continue
    return frozenset(configured_ids)


def _payment_redirect_base_url(server_ip: str, server_port: int) -> str:
    configured = os.getenv("PAYMENT_REDIRECT_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    server_ip = server_ip.strip().rstrip("/")
    if not server_ip:
        return ""
    if server_ip.startswith(("http://", "https://")):
        return server_ip
    if ":" in server_ip:
        return f"http://{server_ip}"
    return f"http://{server_ip}:{server_port}"


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    db_path: str = os.getenv("DB_PATH", "bot_database.db")
    wallet_id: int = _int_env("WALLET_ID", -1)
    url_redis: str = os.getenv("URL_REDIS") or "redis://localhost:6379/0"
    secret_code: str = os.getenv("SECRET_WORD", os.getenv("SERCET_WORD", ""))
    admin_ids: frozenset[int] = _admin_ids()
    afk_timeout: int = _positive_int_env("AFK_TIMEOUT", 24 * 60 * 60)
    afk_check_interval: int = min(
        _positive_int_env("AFK_CHECK_INTERVAL", 60),
        60,
    )
    app_timezone: str = os.getenv("APP_TIMEZONE") or "Asia/Yekaterinburg"
    server_ip: str = os.getenv("SERVER_IP", "")
    payment_redirect_host: str = os.getenv("PAYMENT_REDIRECT_HOST", "0.0.0.0")
    payment_redirect_port: int = _positive_int_env("PAYMENT_REDIRECT_PORT", 5000)
    payment_redirect_base_url: str = _payment_redirect_base_url(
        server_ip,
        payment_redirect_port,
    )


config = Config()
