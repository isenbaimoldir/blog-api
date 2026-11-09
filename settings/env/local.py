from settings.base import *
from settings.conf import BLOG_DEBUG

DEBUG = BLOG_DEBUG

DATABSE = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}