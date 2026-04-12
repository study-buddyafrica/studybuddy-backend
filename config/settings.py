import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = (
    os.getenv("SECRET_KEY") or "sjdfhskjdfhskjdfhskjdfhskjdfhskjdfhskjdfhskjdfh"
)

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    "backend.studybuddy.africa",
    "54.225.241.26",
    "127.0.0.1",
    "localhost",
    "wathi.tail433a8c.ts.net",
    "34.234.64.73",
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
]


SECURE_CONTENT_TYPE_NOSNIFF = True


SECURE_REFERRER_POLICY = "same-origin"

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True  # force HTTPS

SECURE_CONTENT_TYPE_NOSNIFF = True

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
    "http://34.234.64.73:8000"
]

X_FRAME_OPTIONS = "SAMEORIGIN"

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
""" swagger settings"""

SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    }
}

"""JWT settings"""

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=4),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "UPDATE_LAST_LOGIN": True,
    "AUTH_COOKIE": "refresh_token",
    "AUTH_COOKIE_SECURE": not DEBUG,  # True in Production (requires HTTPS)
    "AUTH_COOKIE_HTTP_ONLY": True,  # Blocks XSS attacks from reading it
    "AUTH_COOKIE_SAMESITE": "Lax",  # Protects against CSRF attacks
}

"""spectacular settings:"""
SPECTACULAR_SETTINGS = {
    "TITLE": "StudBuddy",
    "DESCRIPTION": "StudyBuddy API documentation",
    "VERSION": "3.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "filter": True,
        "displayRequestDuration": True,
    },
}

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "rest_framework.schemas.coreapi.AutoSchema",
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
        "anon": "20/m",
        "user": "2000/h",
        "auth": "5/m",
        "burst": "30/m",
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


# if not DEBUG or POSTGRES_LOCALLY:
# if DEBUG:
if DATABASE_URL == "":
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
elif DATABASE_URL == "" and DEBUG:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    print(f"Using datbase: {DATABASE_URL}")
# else:
#     DATABASES = {
#         "default": {
#             "ENGINE": "django.db.backends.sqlite3",
#             "NAME": BASE_DIR / "db.sqlite3",
#         }
#     }
#     print("using sqlite locally")

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

# Email configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = os.getenv("MAIL_PORT")
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("MAIL_USERNAME")
EMAIL_HOST_PASSWORD = os.getenv("MAIL_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("MAIL_DEFAULT_SENDER", EMAIL_HOST_USER)

# google auth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv(
            "REDIS_URL",
            f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB', '0')}",
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# intasend
INTASEND_PUBLISHABLE_KEY = os.getenv("INTASEND_PUBLISHABLE_KEY")
INTASEND_SECRET_KEY = os.getenv("INTASEND_TOKEN")
INTASEND_ENV = ("sandbox",)
INTASEND_WEBHOOK_CHALLENGE = "studyyddubbuddy"


# If we are developing locally, print emails to the terminal instead of actually sending them.
if DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
