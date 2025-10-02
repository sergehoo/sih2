from django.conf.global_settings import LOGGING

from . import DATABASES
from .base import *

DJANGO_ENV = 'prod'
DEBUG = False

# Doivent être fournis par l'env
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [h for h in ENV("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

# Sécurité HTTPS
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(ENV("SECURE_HSTS_SECONDS", "31536000"))  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_REFERRER_POLICY = "same-origin"

DB_URL = os.environ.get("DATABASE_URL", "")

if DB_URL:
    url = urlparse(DB_URL)
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": url.path.lstrip("/"),
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port or "5432",
            "CONN_MAX_AGE": int(os.environ.get("DJANGO_DB_CONN_MAX_AGE", "0")),
            "OPTIONS": {
                "sslmode": os.environ.get("PGSSLMODE", "prefer"),
                "options": "-c statement_timeout=60000",
                "connect_timeout": 10,
                "application_name": os.environ.get("DJANGO_APP_NAME", "sigh"),
            },
            "ATOMIC_REQUESTS": False,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": os.environ.get("DATABASE_NAME", "sihdb"),
            "USER": os.environ.get("DATABASE_USER", "sihuser"),
            "PASSWORD": os.environ.get("DATABASE_PASSWORD", "sihpass"),
            "HOST": os.environ.get("DATABASE_HOST", "localhost"),
            "PORT": os.environ.get("DATABASE_PORT", "5432"),
        }
    }

# Connexions DB : PgBouncer en transaction => CONN_MAX_AGE = 0 conseillé
if "default" in DATABASES:
    DATABASES["default"]["CONN_MAX_AGE"] = int(ENV("DJANGO_DB_CONN_MAX_AGE", "0"))
    # Forcer SSL si souhaité
    opts = DATABASES["default"].setdefault("OPTIONS", {})
    opts["sslmode"] = ENV("PGSSLMODE", "require")



# CORS/CSRF depuis l'env
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [o for o in ENV("CORS_ALLOWED_ORIGINS", "").split(",") if o]
CSRF_TRUSTED_ORIGINS = [o for o in ENV("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Logging prod (moins verbeux)
LOGGING["loggers"]["django"]["level"] = ENV("DJANGO_LOG_LEVEL", "INFO")
LOGGING["loggers"]["django.db.backends"]["level"] = ENV("DJANGO_DB_LOG_LEVEL", "WARNING")

# Prometheus: /metrics exposé par django-prometheus (protège au niveau ingress)
