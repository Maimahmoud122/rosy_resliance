import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ─────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")

    # ── Database ──────────────────────────────────────────
    # SQLALCHEMY_DATABASE_URI = (
    #     f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    #     f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
    # )
    # SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL").replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {
            "sslmode": "require"
        }
    }
    # ── JWT ───────────────────────────────────────────────
    JWT_SECRET_KEY            = os.getenv("JWT_SECRET_KEY", "fallback-jwt-key")
    JWT_ACCESS_TOKEN_EXPIRES  = 3600      # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 2592000   # 30 days

    # ── Mail ──────────────────────────────────────────────
    MAIL_SERVER         = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT           = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS        = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME       = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD       = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")


   # ── Cloudinary ────────────────────────────────────────
    CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY    = os.getenv("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")
 
    # ── Upload ────────────────────────────────────────────
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024   # 10MB max upload size