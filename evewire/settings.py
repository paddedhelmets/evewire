"""
Django settings for evewire project.

For more information, see:
https://docs.djangoproject.com/en/5.1/topics/settings/
"""

from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [s.strip() for s in v.split(',')])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'oauth2_provider',
    'django_q',
    'mptt',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'oauth2_provider.middleware.OAuth2TokenMiddleware',
]

ROOT_URLCONF = 'evewire.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'evewire.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.sqlite3'),
        'NAME': config('DB_NAME', default=BASE_DIR / 'db.sqlite3'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default=''),
    }
}
# Default auto-increment for SQLite
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'core.User'

# Password validation (not used for EVE SSO, but kept for admin)
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Login URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# EVE SSO Configuration
EVE_CLIENT_ID = config('EVE_CLIENT_ID', default='')
EVE_CLIENT_SECRET = config('EVE_CLIENT_SECRET', default='')
EVE_CALLBACK_URL = config('EVE_CALLBACK_URL', default='http://localhost:8000/oauth/callback/')
EVE_SSO_LOGIN_URL = 'https://login.eveonline.com/oauth/authorize'
EVE_SSO_TOKEN_URL = 'https://login.eveonline.com/oauth/token'
EVE_SSO_VERIFY_URL = 'https://login.eveonline.com/oauth/verify'

# ESI Configuration
ESI_BASE_URL = 'https://esi.evetech.net/latest'
ESI_DATASOURCE = 'tranquility'
ESI_COMPATIBILITY_DATE = config('ESI_COMPATIBILITY_DATE', default='2024-01-01')
ESI_SWAGGER_URL = 'https://esi.evetech.net/latest/swagger.json'

# OAuth2 Toolkit Configuration
OAUTH2_PROVIDER = {
    'SCOPES': ['read write'],
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,
    'REFRESH_TOKEN_EXPIRE_SECONDS': 3600 * 24 * 7,  # 7 days
    'AUTHORIZATION_CODE_EXPIRE_SECONDS': 600,
}

# django-q2 Configuration
Q_CLUSTER = {
    'name': 'evewire',
    'workers': config('Q_WORKERS', default=1, cast=int),
    'timeout': config('Q_TIMEOUT', default=30, cast=int),
    'retry': config('Q_RETRY', default=120, cast=int),
    'queue_limit': config('Q_QUEUE_LIMIT', default=50, cast=int),
    'bulk': config('Q_BULK', default=1, cast=int),
    'save_limit': config('Q_SAVE_LIMIT', default=250, cast=int),
    'cpu_affinity': config('Q_CPU_AFFINITY', default=1, cast=int),
    'label': 'Django Q2',
    'redis': {},  # Empty dict to disable redis and force database broker
}

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'evewire.log',
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'] if not DEBUG else ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': config('DJANGO_LOG_LEVEL', default='INFO'), 'propagate': False},
        'evewire': {'handlers': ['console', 'file'] if not DEBUG else ['console'], 'level': 'DEBUG', 'propagate': False},
    },
}

# Security headers (production)
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = config('HTTPS_ONLY', default=False, cast=bool)

# Session configuration
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
