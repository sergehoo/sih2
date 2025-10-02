from .base import *

DJANGO_ENV = 'dev'
DEBUG = True
ALLOWED_HOSTS = ["*"]

# CORS dev : plus permissif
CORS_ALLOW_ALL_ORIGINS = True

# Email en console
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# DB: autorise sqlite si pas de DATABASE_URL
# (hérité de base.py)

# Logging verbeux en dev
# LOGGING["loggers"]["django"]["level"] = "DEBUG"
# LOGGING["loggers"]["django.db.backends"]["level"] = "DEBUG"

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": os.environ.get("DATABASE_NAME", "sihdb"),
        "USER": os.environ.get("DATABASE_USER", "postgres"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "weddingLIFE18"),
        "HOST": os.environ.get("DATABASE_HOST", "localhost"),
        "PORT": os.environ.get("DATABASE_PORT", "5433"),
        "CONN_MAX_AGE": 60,  # connexion persistante modérée en local
        "OPTIONS": {
            "sslmode": os.environ.get("PGSSLMODE", "prefer"),
            "application_name": "sigh-local",
        },
    }
}