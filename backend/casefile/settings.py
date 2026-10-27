"""Django settings for Casefile.

All environment-specific values come from environment variables (or the repo-root
`.env` file in local development). See `.env.example` and docs/ARCHITECTURE.md §9.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
REPO_ROOT = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CSRF_TRUSTED_ORIGINS=(list, []),
    GUEST_RETENTION_DAYS=(int, 90),
    PUBLIC_ORIGIN=(str, ""),
)
# Local development reads the repo-root .env; in CI and on Render, real env vars win.
environ.Env.read_env(REPO_ROOT / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY")  # required: no default, so a missing key fails loudly
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")
# Origin used in emailed links, e.g. https://casefile.example. Empty: use the request's host.
PUBLIC_ORIGIN = env("PUBLIC_ORIGIN")
# D-22 (open): guest sessions and inactive guest data last this many days.
GUEST_RETENTION_DAYS = env("GUEST_RETENTION_DAYS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "accounts",
    "content",
    "play",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "casefile.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "casefile.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL")}

AUTH_USER_MODEL = "accounts.User"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Build-time output of `manage.py collect_case_assets`:
# content-hashed case images (ARCHITECTURE §7).
CASE_ASSETS_DIR = BASE_DIR / "static_src"
STATICFILES_DIRS = [CASE_ASSETS_DIR]
CASES_DIR = REPO_ROOT / "content" / "cases"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Cookies: secure everywhere except local DEBUG. SameSite=Lax suits the same-origin SPA.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # the SPA reads it to send X-CSRFToken
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # accounts: 2 weeks; guests get GUEST_RETENTION_DAYS

# Email: printed to the console until a provider is chosen (D-17, M20).
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Casefile <no-reply@casefile.local>")

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "casefile.api.authentication.CsrfSessionAuthentication",
    ],
    # Deny by default; each view opts in to its access level (Public, Player, Account, Staff).
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "casefile.api.exceptions.exception_handler",
    "DEFAULT_THROTTLE_RATES": {"auth_ip": "10/min", "auth_account": "5/min"},
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Casefile API",
    "DESCRIPTION": "REST API for the Casefile mystery investigation platform (docs/API_PLAN.md).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
