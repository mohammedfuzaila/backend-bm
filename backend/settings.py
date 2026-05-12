import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-g($&#9zofdqx0bf&68qtgsxpfg!!nr^n2#@(ewz0y5(2m4d#pl')
DEBUG = os.environ.get('DEBUG', 'False') == 'True'
ALLOWED_HOSTS = [
    'backend-bm-9abv.onrender.com',
    'localhost',
    '127.0.0.1',
    '.onrender.com',
    '*',
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'api',
]

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

ROOT_URLCONF = 'backend.urls'

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

WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'api.User'

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://bachmates.netlify.app",
    "https://bm-adminpanel.netlify.app",
    "https://www.bachmates.netlify.app",
]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://.*\.netlify\.app$",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_METHODS = [
    "DELETE",
    "GET",
    "OPTIONS",
    "PATCH",
    "POST",
    "PUT",
]
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]
CORS_PREFLIGHT_MAX_AGE = 86400

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "https://*.netlify.app",
    "https://bachmates.netlify.app",
    "https://bm-adminpanel.netlify.app",
    "https://www.bachmates.netlify.app",
    "https://backend-bm-9abv.onrender.com",
]

RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')
if not RENDER_EXTERNAL_URL and os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    RENDER_EXTERNAL_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"

if RENDER_EXTERNAL_URL:
    if RENDER_EXTERNAL_URL not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(RENDER_EXTERNAL_URL)
    BACKEND_URL = RENDER_EXTERNAL_URL
else:
    BACKEND_URL = "https://backend-bm-9abv.onrender.com"

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'anaikarmohammedfuzail57@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'zrowwvzmqovvbyra')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'BachMates <anaikarmohammedfuzail57@gmail.com>')
EMAIL_TIMEOUT = 10

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Session and Cookie settings for Cross-Domain (Netlify <-> Render)
if not DEBUG:
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_SECURE = True  # Required for SameSite=None
    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_COOKIE_SECURE = True
else:
    # Local development settings
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SECURE = False

SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_HTTPONLY = False # Allow frontend to read for headers if needed
