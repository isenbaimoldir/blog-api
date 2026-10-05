from decouple import config

BLOG_ENV_ID: str = config("BLOG_ENV_ID", default="local")
BLOG_SECRET_KEY: str = config("BLOG_SECRET_KEY")
BLOG_DEBUG: bool = config("BLOG_DEBUG", default=True, cast=bool)