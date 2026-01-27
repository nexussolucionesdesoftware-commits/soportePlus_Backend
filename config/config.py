import os
from datetime import timedelta

from decouple import config

# Detectar la ruta base del proyecto para los archivos
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration class."""

    # Flask
    SECRET_KEY = config("SECRET_KEY")  # Sin default para forzar el uso del .env
    DEBUG = False
    TESTING = False

    # Database
    # Centralizamos la URI para no repetir configuraciones sensibles
    SQLALCHEMY_DATABASE_URI = config("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    # JWT
    JWT_SECRET_KEY = config("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # CORS
    CORS_ORIGINS = config("CORS_ORIGINS", default="*")

    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    # Ruta dinámica para que funcione en cualquier carpeta de tu Fedora
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "..", "app", "static", "uploads")


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    # En desarrollo usamos la misma del .env o una específica si la tienes
    SQLALCHEMY_DATABASE_URI = config("DEV_DATABASE_URL", default=config("DATABASE_URL"))

    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 300, "pool_pre_ping": True}


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False
    # En producción NO hay defaults, debe venir del entorno
    SQLALCHEMY_DATABASE_URI = config("DATABASE_URL")

    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
