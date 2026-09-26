import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = (
    os.getenv("SECRET_KEY") or "sjdfhskjdfhskjdfhskjdfhskjdfhskjdfhskjdfhskjdfh"
)

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    "*"
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_standardized_errors",
    "whitenoise",
    "djmoney",
    # third party app
    "apps.users",
    "apps.core",
    "apps.school",
    "apps.transactions",
    "apps.calendar",
]

"""Security Headers"""
SECURE_CONTENT_TYPE_NOSNIFF = True # (good)
SECURE_REFERRER_POLICY = "same-origin" # (good)
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin" # (good)
SECURE_HSTS_SECONDS = 31536000 # 1 year (good)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True # (good)
SECURE_HSTS_PRELOAD = True # (good)
if not DEBUG:
    SECURE_SSL_REDIRECT = True  # force HTTPS

"""# Content Security Policy settings"""
CSP_DEFAULT_SRC = ("'none'",)

"""# Allow embedding in iframes from these specific origins"""
CSP_FRAME_ANCESTORS = (
    "'self'",
    "http://localhost:5173",
    "http://localhost:3000",
    "https://studybuddy.africa",
    "https://www.studybuddy.africa",
    "http://localhost:5174",
    "https://studybuddy-frotend.vercel.app",
)

CSP_SCRIPT_SRC = ("'self'",)
CSP_STYLE_SRC = "'self'"

CORS_ALLOW_ALL_HEADERS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://studybuddy.africa",
    "https://www.studybuddy.africa",
    "http://0.0.0.0:8000",
    "https://studybuddy-frotend.vercel.app",
    "https://studybuddy-frotend-staging.vercel.app",
    "https://studybuddy-backend-6vya.onrender.com",
]

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https:\/\/.*\.vercel\.app$",
    r"^https:\/\/.*\.studybuddy\.africa$",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "GET",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
    "OPTIONS",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://studybuddy.africa",
    "https://www.studybuddy.africa",
    "http://34.234.64.73:8000",
    "https://studybuddy-frotend.vercel.app",
    "https://studybuddy-frotend-staging.vercel.app",
    "https://studybuddy-backend-6vya.onrender.com",
    "https://*.vercel.app",
]

X_FRAME_OPTIONS = "SAMEORIGIN"

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

"""Swagger Settings"""
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    }
}

"""JWT settings"""
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=4), # Access tokens are valid for 4 hours
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14), # Refresh tokens are valid for 14 days
    "UPDATE_LAST_LOGIN": True, # Update the last login time when a user logs in
    "ROTATE_REFRESH_TOKENS": True, # Rotate refresh tokens when they are used
    "BLACKLIST_AFTER_ROTATION": True, # Blacklist refresh tokens after they are used
    "AUTH_COOKIE": "refresh_token", # The name of the cookie to store the refresh token
    "AUTH_COOKIE_SECURE": not DEBUG,  # True in Production (requires HTTPS)
    "AUTH_COOKIE_HTTP_ONLY": True,  # Blocks XSS attacks from reading it
    "AUTH_COOKIE_SAMESITE": "None",  # Protects against CSRF attacks
}

"""spectacular settings:"""
SPECTACULAR_SETTINGS = {
    "TITLE": "StudBuddy",
    "DESCRIPTION": "StudyBuddy API documentation",
    "VERSION": "3.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "PREPROCESSING_HOOKS": [
        "apps.core.schema_hooks.preprocess_api_canonical_endpoints",
    ],
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "filter": True,
        "displayRequestDuration": True,
    },
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ]
    if not DEBUG
    else [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 5,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/m", # Anon users are limited to 20 requests per minute
        "user": "2000/h", # Authenticated users are limited to 2000 requests per hour
        "auth": "5/m", # Authenticated users are limited to 5 requests per minute
        "burst": "10/m", # Burst requests are limited to 10 per minute
        "login": "5/m", # Login requests are limited to 5 per minute
        "public": "60/m", # Public endpoints are limited to 60 requests per minute
    },
}
DRF_STANDARDIZED_ERRORS = {"ENABLE_IN_DEBUG_FOR_UNHANDLED_EXCEPTIONS": False}

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

DATABASE_URL = os.getenv("DATABASE_URL", "")
POSTGRES_LOCALLY = os.getenv("POSTGRES_LOCALLY", default=False)


if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    if DEBUG:
        db_host = DATABASES["default"].get("HOST", "unknown")
        print(f"Connected to database host: {db_host}")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "myproject_db"),
            "USER": os.getenv("DB_USER", "your_postgres_user"),
            "PASSWORD": os.getenv("DB_PASSWORD", "your_password"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

APPEND_SLASH = True

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "core.User"

def _env_first(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value
    return default


def _env_first_stripped(*names: str, default: str = "") -> str | None:
    value = _env_first(*names, default=default).strip()
    return value or None


def _env_bool(*names: str, default: str = "false") -> bool:
    return _env_first(*names, default=default).lower() in ("true", "1", "yes")


def get_email_backend() -> str:
    """Prefer explicit env override, then SMTP when credentials exist; otherwise fall back to console in local debug mode."""
    explicit_backend = _env_first("EMAIL_BACKEND", default=None)
    if explicit_backend:
        return explicit_backend
    email_address = _env_first_stripped("EMAIL_HOST_USER", "MAIL_USERNAME")
    email_password = _env_first_stripped("EMAIL_HOST_PASSWORD", "MAIL_PASSWORD")
    email_debug_console = _env_bool(
        "EMAIL_DEBUG_CONSOLE", "MAIL_DEBUG_CONSOLE", default="true"
    )

    if email_address and email_password:
        return "django.core.mail.backends.smtp.EmailBackend"
    if DEBUG and email_debug_console:
        return "django.core.mail.backends.console.EmailBackend"
    return "django.core.mail.backends.smtp.EmailBackend"


# Email Configuration
EMAIL_BACKEND = get_email_backend()
EMAIL_HOST = _env_first("EMAIL_HOST", "MAIL_HOST", default="smtp.gmail.com")
EMAIL_HOST_USER = _env_first_stripped("EMAIL_HOST_USER", "MAIL_USERNAME")
EMAIL_HOST_PASSWORD = _env_first_stripped("EMAIL_HOST_PASSWORD", "MAIL_PASSWORD")
EMAIL_PORT = int(_env_first("EMAIL_PORT", "MAIL_PORT", default="587"))
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", "MAIL_USE_TLS", default="true")
DEFAULT_FROM_EMAIL = _env_first(
    "EMAIL_DEFAULT_SENDER",
    "MAIL_DEFAULT_SENDER",
    default="noreply@studybuddy.africa",
)
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() in ("true", "1", "yes")
EMAIL_DEBUG_CONSOLE = _env_bool("EMAIL_DEBUG_CONSOLE", "MAIL_DEBUG_CONSOLE", default="true")
EMAIL_TIMEOUT = int(_env_first("EMAIL_TIMEOUT", default="5"))
EXPOSE_VERIFICATION_CODE = _env_bool("EXPOSE_VERIFICATION_CODE", default="false")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
BREVO_API_KEY = os.getenv("BREVO_API_KEY")

# google auth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Redis / Cache Configuration
REDIS_URL = os.getenv("REDIS_URL")
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")

# Use Redis only when an external URL or valid remote host is provided
if REDIS_URL and not any(h in REDIS_URL for h in ("127.0.0.1", "localhost")):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
elif REDIS_HOST and REDIS_HOST not in ("127.0.0.1", "localhost", "0.0.0.0"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": f"redis://{REDIS_HOST}:{REDIS_PORT}/1",
        }
    }
else:
    # Graceful in-memory cache fallback for single-container production and local development
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "studybuddy-bridge-cache",
        }
    }

# intasend
INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")
INTASEND_SECRET_KEY = os.getenv("INTASEND_TOKEN")
INTASEND_ENV = ("sandbox",)
INTASEND_WEBHOOK_CHALLENGE = "studyyddubbuddy"

# Paystack
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")

# Platform fee percentage deducted from escrow before teacher payout
PLATFORM_FEE_PERCENT = float(os.getenv("PLATFORM_FEE_PERCENT", "10"))

# Base URL for generated session meeting links
BASE_URL = os.getenv("BASE_URL", "https://meet.studybuddy.africa")
SESSION_BASE_URL = os.getenv("SESSION_BASE_URL", f"{BASE_URL}/sessions")

# Jitsu analytics API
JITSU_API_KEY = os.getenv("JITSU_API_KEY", "")
JITSU_API_URL = os.getenv("JITSU_API_URL", "")

# Excalidraw whiteboard API
EXCALIDRAW_API_KEY = os.getenv("EXCALIDRAW_API_KEY", "")
EXCALIDRAW_API_URL = os.getenv("EXCALIDRAW_API_URL", "https://api.excalidraw.com")
EXCALIDRAW_APP_URL = os.getenv("EXCALIDRAW_APP_URL", "https://excalidraw.com/")
DEFAULT_WHITEBOARD_LINK = os.getenv("DEFAULT_WHITEBOARD_LINK", EXCALIDRAW_APP_URL)
