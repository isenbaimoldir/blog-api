from decouple import config

BLOG_SECRET_KEY: str = config(
    "BLOG_SECRET_KEY", 
    default="django-insecure-secret-key-for-local-dev-12345"
)
BLOG_DEBUG: bool = config("BLOG_DEBUG", default=True, cast=bool)
BLOG_ENV_ID: str = config("BLOG_ENV_ID", default="local")