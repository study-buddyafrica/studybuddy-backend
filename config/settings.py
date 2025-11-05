import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url 

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY =os.getenv("SECRET_KEY")

DEBUG = os.getenv('DEBUG')

ALLOWED_HOSTS = ["backend.studybuddy.africa",'54.225.241.26']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_standardized_errors',
    'whitenoise',
    'djmoney',
    # third party app
    'apps.users',
    'apps.core',
    'apps.school',
    'apps.transactions',


]


X_FRAME_OPTIONS = 'ALLOWALL'

SECURE_CONTENT_TYPE_NOSNIFF = True

"""# Content Security Policy settings"""
CSP_DEFAULT_SRC = ("'self'",)

"""# Allow embedding in iframes from these specific origins"""
CSP_FRAME_ANCESTORS = ("'self'", 
                        "http://localhost:5173",
                        "http://localhost:3000",
                        "https://studybuddy.africa",
                        "http://localhost:5174")


CORS_ALLOW_ALL_HEADERS = True
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5174',
    "https://studybuddy.africa",
]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://localhost:5174',
    "https://studybuddy.africa",

]


"""# swagger settings"""

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}

"""JWT settings"""

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=4  ),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),

}

"""spectacular settings:"""
SPECTACULAR_SETTINGS = {
    'TITLE': 'StudBuddy',
    'DESCRIPTION': 'StudyBuddy API documentation',
    'VERSION': '3.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
}


REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 5,
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    "EXCEPTION_HANDLER": "drf_standardized_errors.handler.exception_handler"

}
DRF_STANDARDIZED_ERRORS = {"ENABLE_IN_DEBUG_FOR_UNHANDLED_EXCEPTIONS": False}

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

POSTGRES_LOCALLY = True
DATABASES = {}

if DEBUG == False or POSTGRES_LOCALLY == True:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('TEST_DATABASE_URI')
        )

    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True



STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

if os.getenv('RAILWAY_ENVIRONMENT'):
    MEDIA_ROOT = '/app/media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL ='core.User'


# Email configuration
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = os.getenv("MAIL_PORT")
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("MAIL_USERNAME")
EMAIL_HOST_PASSWORD = os.getenv("MAIL_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("MAIL_DEFAULT_SENDER", EMAIL_HOST_USER)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}   

