import os
from pathlib import Path
from datetime import timedelta
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # .../sigh
ENV = os.environ.get

# -----------------------
#  Sécurité de base
# -----------------------
SECRET_KEY = ENV("DJANGO_SECRET_KEY", "change-me-in-prod")
DEBUG = ENV("DJANGO_DEBUG", "False").lower() == "true"
ALLOWED_HOSTS = [h for h in ENV("DJANGO_ALLOWED_HOSTS", "").split(",") if h] or []

# -----------------------
#  Applications
# -----------------------
INSTALLED_APPS = [
    # Prometheus doit entourer Django pour collecter des métriques
    "django_prometheus",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # GeoDjango
    "django.contrib.gis",
    "import_export",

    # Tiers
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    'rest_framework_simplejwt',
    "hospital",
    "pharmacy",
    "finances",
    "human_ressource",
    "laboratory",
    "logistic",

]

# -----------------------
#  Middleware
# -----------------------
MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",

    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Middleware qui positionne les variables de session Postgres pour la RLS
    # (tu dois créer core/middleware/db_scope.py comme on l’a vu plus haut)
    "core.middleware.db_scope.PostgresScopeMiddleware",

    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "sigh.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {

            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "hospital.context_processors.user_profile",

            ],
        },
    },
]

WSGI_APPLICATION = "sigh.wsgi.application"
ASGI_APPLICATION = "sigh.asgi.application"

# -----------------------
#  Base de données
# -----------------------
# Par défaut, on vise Postgres via PgBouncer (pooling transaction)
# Exemple d’URL: postgresql://user:pass@pgbouncer:6432/sihdb

REDIS_URL = ENV("REDIS_URL", "redis://127.0.0.1:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            # "PASSWORD": ENV("REDIS_PASSWORD", "") or None,
        },
        "TIMEOUT": int(ENV("CACHE_TIMEOUT", "300")),
    }
}

# Sessions stockées en cache Redis
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# Celery (si tu l’utilises)
CELERY_BROKER_URL = ENV("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = ENV("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = ENV("CELERY_TASK_EAGER", "False").lower() == "true"

# -----------------------
#  Internationalisation
# -----------------------
LANGUAGE_CODE = ENV("LANGUAGE_CODE", "fr-fr")
TIME_ZONE = ENV("TIME_ZONE", "Africa/Abidjan")
USE_I18N = True
USE_TZ = True

# -----------------------
#  Static & Media
# -----------------------
STATIC_URL = "/static/"
STATIC_ROOT = ENV("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
MEDIA_ROOT = ENV("DJANGO_MEDIA_ROOT", str(BASE_DIR / "media"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------
#  Auth / OIDC / JWT
# -----------------------
# Le frontend patient/staff obtient un JWT OIDC signé par Keycloak.
# DRF le valide (via simplejwt + clé publique) ou tu places un proxy d’auth devant.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": int(ENV("DJANGO_PAGE_SIZE", "50")),
}
# SIMPLE_JWT = {
#     "ALGORITHM": "RS256",
#     # On vérifie via JWKS — ne pas renseigner SIGNING/VERIFYING_KEY
#     "SIGNING_KEY": None,
#     "VERIFYING_KEY": None,
#
#     # IMPORTANT: drf-simplejwt >= 5.x
#     "JWK_URL": f"{ENV('OIDC_ISSUER')}/protocol/openid-connect/certs",
#
#     "ISSUER": ENV("OIDC_ISSUER"),
#     "AUDIENCE": ENV("OIDC_AUDIENCE", "sih-api"),
#
#     "AUTH_HEADER_TYPES": ("Bearer",),
#     "USER_ID_CLAIM": "sub",  # subject Keycloak
#     "LEEWAY": 30,
#     "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(ENV("JWT_ACCESS_MIN", "30"))),
# }
# SimpleJWT (si tu vérifies localement la clé publique)
SIMPLE_JWT = {
    "ALGORITHM": "RS256",
    "SIGNING_KEY": None,  # on vérifie via la clé publique
    "VERIFYING_KEY": ENV("JWT_VERIFYING_KEY", ""),  # colle la PEM publique si tu ne fais pas JWKS
    "AUDIENCE": ENV("OIDC_AUDIENCE", "sih-api"),
    "ISSUER": ENV("OIDC_ISSUER", "https://sso.example.ci/realms/sih"),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(ENV("JWT_ACCESS_MIN", "30"))),
    "USER_ID_CLAIM": "sub",
}


# -----------------------
#  CORS / CSRF
# -----------------------
CORS_ALLOW_ALL_ORIGINS = ENV("CORS_ALLOW_ALL", "False").lower() == "true"
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = [o for o in ENV("CORS_ALLOWED_ORIGINS", "").split(",") if o]

CSRF_TRUSTED_ORIGINS = [o for o in ENV("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# -----------------------
#  Cache / Sessions / Celery
# -----------------------


SESSION_ENGINE = ENV("DJANGO_SESSION_ENGINE", "django.contrib.sessions.backends.cached_db")

# Celery
CELERY_BROKER_URL = ENV("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = ENV("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = ENV("CELERY_TASK_EAGER", "False").lower() == "true"

# -----------------------
#  Email
# -----------------------
EMAIL_BACKEND = ENV("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = ENV("EMAIL_HOST", "localhost")
EMAIL_PORT = int(ENV("EMAIL_PORT", "25"))
EMAIL_HOST_USER = ENV("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = ENV("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = ENV("EMAIL_USE_TLS", "False").lower() == "true"
DEFAULT_FROM_EMAIL = ENV("DEFAULT_FROM_EMAIL", "no-reply@sigh.local")

# -----------------------
#  Sécurité (base)
# -----------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")  # si derrière Traefik/Nginx
X_FRAME_OPTIONS = "DENY"

