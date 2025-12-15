import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'zemi_escrow.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'zemi_escrow.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
}

def env(key: str, default=None, *, required=False):
    value = os.getenv(key, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value

DJANGO_ENV = env("DJANGO_ENV", "development")
MPESA_ENVIRONMENT = env("MPESA_ENVIRONMENT", "sandbox")

# M-Pesa Configuration
MPESA_CONSUMER_KEY = env("MPESA_CONSUMER_KEY", required=True)
MPESA_CONSUMER_SECRET = env("MPESA_CONSUMER_SECRET", required=True)
MPESA_SHORTCODE = env("MPESA_SHORTCODE", required=True)
MPESA_PASSKEY = env("MPESA_PASSKEY", required=True)
MPESA_INITIATOR_NAME = env("MPESA_INITIATOR_NAME", required=True)
MPESA_SECURITY_CREDENTIAL = env("MPESA_SECURITY_CREDENTIAL", required=True)
MPESA_CALLBACK_URL = env(
    "MPESA_CALLBACK_URL",
    "http://127.0.0.1:4040/api/webhooks/mpesa/"
)

MPESA_B2C_QUEUE_TIMEOUT_URL = env(
    "MPESA_B2C_QUEUE_TIMEOUT_URL",
    "http://127.0.0.1:4040/api/webhooks/mpesa-b2c-timeout/"
)

MPESA_B2C_RESULT_URL = env(
    "MPESA_B2C_RESULT_URL",
    "http://127.0.0.1:4040/api/webhooks/mpesa-b2c-result/"
)

# # Stripe Configuration
# STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')
# STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
# STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')