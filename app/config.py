import os
from dotenv import load_dotenv

load_dotenv()

def _get_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes")

def _get_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Cafe Rewards")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = _get_bool("DEBUG", False)

    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _get_int("ACCESS_TOKEN_EXPIRE_MINUTES", 1440)
    COOKIE_NAME: str = os.getenv("COOKIE_NAME", "cafe_session")

    OTP_LENGTH: int = _get_int("OTP_LENGTH", 6)
    OTP_EXPIRE_MINUTES: int = _get_int("OTP_EXPIRE_MINUTES", 5)

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./cafe_rewards.db")

    RUPEES_PER_POINT: int = _get_int("RUPEES_PER_POINT", 5)
    POINT_REDEMPTION_VALUE: int = _get_int("POINT_REDEMPTION_VALUE", 1)

    SIMULATE_EMAIL: bool = _get_bool("SIMULATE_EMAIL", True)

settings = Settings()

if not settings.SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env")