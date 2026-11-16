from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import connection
from django.db.models import Model, QuerySet
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.blog.models import Post
from apps.blog.queries import QUERIES


class Command(BaseCommand):
    help = "Run ORM queries and print results and SQL counts."

    MUTATING_NUMBERS = (40, 41, 42, 43, 44)
    PREVIEW_LIMIT = 5
    SAMPLE_PAGE = 1
    SAMPLE_WORD = "the"
    SAMPLE_DOMAIN = "gmail.com"
    SAMPLE_CATEGORY_SLUGS = ["python", "django"]
    SAMPLE_LAST_DAYS = 90
    SAMPLE_BETWEEN_DAYS = 180
    SAMPLE_TAG_SLUG = "django-orm"
    SAMPLE_SECOND_TAG_SLUG = "pytest"
    SAMPLE_CATEGORY_SLUG = "python"
    SAMPLE_SEARCH_TEXT = "the"
    SAMPLE_MIN_POSTS = 2
    SAMPLE_NAME_TEXT = "a"
    SAMPLE_TAG_NAME = "FastAPI"
    SAMPLE_DRAFT_DAYS = 180
    SAMPLE_SOURCE_CATEGORY = "machine"
    SAMPLE_TARGET_CATEGORY = "python"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--number",
            type=int,
            default=None,
            help="Run a single query by number",
        )
        parser.add_argument(
            "--sql",
            action="store_true",
            help="Print SQL queries sent to the database",
        )

    def __sample_arguments(self) -> dict[int, dict[str, Any]]:
        now: datetime = timezone.now()
        post: Post | None = (
            Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
            .select_related("author")
            .first()
        )
        slug: str = post.slug if post else "sample-post"
        email: str = post.author.email if post else "user@gmail.com"
        year: int = post.created_at.year if post else now.year
        month: int = post.created_at.month if post else now.month

        return {
            4: {"slug": slug},
            7: {"page": self.SAMPLE_PAGE},
            8: {"word": self.SAMPLE_WORD},
            9: {"domain": self.SAMPLE_DOMAIN},
            11: {"slugs": self.SAMPLE_CATEGORY_SLUGS},
            12: {"year": year, "month": month},
            13: {"days": self.SAMPLE_LAST_DAYS},
            14: {
                "start": (now - timedelta(days=self.SAMPLE_BETWEEN_DAYS)).date(),
                "end": now.date(),
            },
            15: {"email": email},
            16: {"tag_slug": self.SAMPLE_TAG_SLUG},
            17: {"category_slug": self.SAMPLE_CATEGORY_SLUG},
            21: {
                "first_slug": self.SAMPLE_TAG_SLUG,
                "second_slug": self.SAMPLE_SECOND_TAG_SLUG,
            },
            22: {"text": self.SAMPLE_SEARCH_TEXT},
            34: {"min_posts": self.SAMPLE_MIN_POSTS},
            37: {"text": self.SAMPLE_NAME_TEXT},
            40: {"name": self.SAMPLE_TAG_NAME},
            41: {"days": self.SAMPLE_DRAFT_DAYS},
            42: {
                "category_slug": self.SAMPLE_CATEGORY_SLUG,
                "tag_slug": self.SAMPLE_TAG_SLUG,
            },
            43: {
                "source_slug": self.SAMPLE_SOURCE_CATEGORY,
                "target_slug": self.SAMPLE_TARGET_CATEGORY,
            },
        }

    def __format_row(self, row: Any, annotations: list[str]) -> str:
        if isinstance(row, Model) and annotations:
            extra: dict[str, Any] = {
                key: getattr(row, key) for key in annotations if hasattr(row, key)
            }
            return f"{row} {extra}"
        return str(row)

    def __print_output(
        self,
        number: int,
        name: str,
        result: Any,
        annotations: list[str],
        queries: list[dict[str, str]],
        show_sql: bool,
    ) -> None:
        count: int = len(queries)
        word: str = "query" if count == 1 else "queries"
        self.stdout.write(f"{number} {name} — {count} SQL {word}")

        if show_sql:
            for item in queries:
                self.stdout.write(item["sql"])

        if isinstance(result, list):
            for row in result[: self.PREVIEW_LIMIT]:
                self.stdout.write(self.__format_row(row, annotations))
            self.stdout.write(f"({len(result)} rows)")
        elif isinstance(result, dict):
            for key, value in list(result.items())[: self.PREVIEW_LIMIT]:
                self.stdout.write(f"{key}: {value}")
            if len(result) > self.PREVIEW_LIMIT:
                self.stdout.write(f"({len(result)} entries)")
        else:
            self.stdout.write(str(result))

    def handle(self, *args: tuple[Any, ...], **options: dict[str, Any]) -> None:
        number: int | None = options["number"]
        show_sql: bool = options["sql"]

        if number is not None and number not in QUERIES:
            raise CommandError(f"Query {number} does not exist.")

        sample_args: dict[int, dict[str, Any]] = self.__sample_arguments()
        numbers: list[int] = (
            [number]
            if number is not None
            else [num for num in sorted(QUERIES) if num not in self.MUTATING_NUMBERS]
        )

        for num in numbers:
            func: Callable[..., Any] = QUERIES[num]
            kwargs: dict[str, Any] = sample_args.get(num, {})
            annotations: list[str] = []

            with CaptureQueriesContext(connection) as context:
                result: Any = func(**kwargs)
                if isinstance(result, QuerySet):
                    annotations = list(result.query.annotations.keys())
                    result = list(result)

            self.__print_output(
                number=num,
                name=func.__name__,
                result=result,
                annotations=annotations,
                queries=context.captured_queries,
                show_sql=show_sql,
            )