from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'factwise-standalone-secret-key'
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = ['planner']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'db.sqlite3',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
TIME_ZONE = 'UTC'
