from datetime import datetime, timedelta
import random
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone
from django.utils.text import slugify
from faker import Faker

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()


class Command(BaseCommand):
    help = "Fill the database with fake data."

    DEFAULT_USERS = 20
    DEFAULT_POSTS = 100
    DEFAULT_COMMENTS = 500
    DEFAULT_PASSWORD = "password123"
    DAYS_IN_YEAR = 365
    EDITED_POST_RATIO = 0.3
    MIN_EDIT_DAYS = 1
    MAX_EDIT_DAYS = 30

    CATEGORIES = (
        "Python",
        "Django",
        "DevOps",
        "C++",
        "Frontend",
        "Backend",
        "DataBase",
        "Machine",
    )

    TAGS = (
        "asyncio",
        "pytest",
        "Django REST Framework",
        "Django ORM",
        "Docker",
        "Kubernetes",
        "CI/CD Pipelines",
        "Standard Template Library (STL)",
        "Smart Pointers",
        "React.js",
        "Tailwind CSS",
        "TypeScript",
        "REST API Design",
        "GraphQL",
        "WebSockets",
        "PostgreSQL",
        "Redis Caching",
        "MongoDB",
        "Scikit-Learn",
        "PyTorch",
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--users",
            type=int,
            default=self.DEFAULT_USERS,
            help="Number of users to create",
        )
        parser.add_argument(
            "--posts",
            type=int,
            default=self.DEFAULT_POSTS,
            help="Number of posts to create",
        )
        parser.add_argument(
            "--comments",
            type=int,
            default=self.DEFAULT_COMMENTS,
            help="Number of comments to create",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def __clear_data(self) -> None:
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Category.objects.all().delete()
        Tag.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def __create_categories_and_tags(self) -> tuple[list[Category], list[Tag]]:
        existing_categories: set[str] = set(
            Category.objects.values_list("name", flat=True)
        )
        new_categories: list[Category] = [
            Category(name=name, slug=slugify(name))
            for name in self.CATEGORIES
            if name not in existing_categories
        ]
        Category.objects.bulk_create(new_categories)

        existing_tags: set[str] = set(Tag.objects.values_list("name", flat=True))
        new_tags: list[Tag] = [
            Tag(name=name, slug=slugify(name))
            for name in self.TAGS
            if name not in existing_tags
        ]
        Tag.objects.bulk_create(new_tags)

        return list(Category.objects.all()), list(Tag.objects.all())

    def __create_users(self, count: int, fake: Faker) -> int:
        hashed_password: str = make_password(self.DEFAULT_PASSWORD)
        existing_emails: set[str] = set(User.objects.values_list("email", flat=True))
        users_to_create: list[User] = []

        i: int
        for i in range(count):
            first_name: str = fake.first_name()
            last_name: str = fake.last_name()
            email: str = f"{first_name.lower()}.{last_name.lower()}@gmail.com"

            suffix: int = 1
            while email in existing_emails:
                email = f"{first_name.lower()}.{last_name.lower()}{suffix}@gmail.com"
                suffix += 1
            existing_emails.add(email)

            user_kwargs: dict[str, Any] = {
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_password,
                "is_active": random.random() > 0.1,
                "is_staff": random.random() < 0.15,
            }
            if hasattr(User, "username"):
                user_kwargs["username"] = email

            users_to_create.append(User(**user_kwargs))

        User.objects.bulk_create(users_to_create)
        return len(users_to_create)

    def __create_posts(
        self,
        count: int,
        users: list[User],
        categories: list[Category],
        tags: list[Tag],
        fake: Faker,
    ) -> list[Post]:
        used_slugs: set[str] = set(Post.objects.values_list("slug", flat=True))
        posts_to_create: list[Post] = []
        created_slugs: list[str] = []

        i: int
        for i in range(count):
            title: str = fake.sentence().rstrip(".")
            base_slug: str = slugify(title)
            slug: str = base_slug

            suffix: int = 2
            while slug in used_slugs:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slugs.add(slug)
            created_slugs.append(slug)

            author: User = random.choice(users)
            body_text: str = "\n\n".join(fake.paragraphs(nb=3))
            status: str = (
                Post.StatusChoices.PUBLISHED
                if random.random() < 0.7
                else Post.StatusChoices.DRAFT
            )
            category: Category | None = (
                random.choice(categories)
                if random.random() > 0.1 and categories
                else None
            )

            posts_to_create.append(
                Post(
                    author=author,
                    title=title,
                    slug=slug,
                    body=body_text,
                    category=category,
                    status=status,
                )
            )

        Post.objects.bulk_create(posts_to_create)
        saved_posts: list[Post] = list(Post.objects.filter(slug__in=created_slugs))

        now: datetime = timezone.now()
        year_seconds: int = int(timedelta(days=self.DAYS_IN_YEAR).total_seconds())

        post: Post
        for post in saved_posts:
            random_offset: int = random.randint(0, year_seconds)
            created_at: datetime = now - timedelta(seconds=random_offset)
            post.created_at = created_at

            if random.random() < self.EDITED_POST_RATIO:
                edit_days: int = random.randint(
                    self.MIN_EDIT_DAYS, self.MAX_EDIT_DAYS
                )
                edited_at: datetime = created_at + timedelta(days=edit_days)
                post.updated_at = edited_at if edited_at <= now else now
            else:
                post.updated_at = created_at

        if saved_posts:
            Post.objects.bulk_update(saved_posts, ["created_at", "updated_at"])

        if tags and saved_posts:
            for post in saved_posts:
                tag_count: int = random.randint(0, min(5, len(tags)))
                if tag_count > 0:
                    post.tags.set(random.sample(tags, tag_count))

        return saved_posts

    def __create_comments(
        self,
        count: int,
        users: list[User],
        published_posts: list[Post],
        fake: Faker,
    ) -> int:
        comments_to_create: list[Comment] = []
        now: datetime = timezone.now()

        i: int
        for i in range(count):
            author: User = random.choice(users)
            post: Post = random.choice(published_posts)
            body_text: str = " ".join(fake.sentences(nb=random.randint(1, 3)))
            comments_to_create.append(
                Comment(
                    post=post,
                    author=author,
                    body=body_text,
                )
            )

        created_comments: list[Comment] = Comment.objects.bulk_create(
            comments_to_create
        )

        comment: Comment
        for comment in created_comments:
            max_seconds: int = max(
                0, int((now - comment.post.created_at).total_seconds())
            )
            offset_seconds: int = random.randint(0, max_seconds)
            comment.created_at = comment.post.created_at + timedelta(
                seconds=offset_seconds
            )

        if created_comments:
            Comment.objects.bulk_update(created_comments, ["created_at"])

        return len(created_comments)

    def handle(self, *args: tuple[Any, ...], **options: dict[str, Any]) -> None:
        start_time: datetime = datetime.now()
        fake: Faker = Faker()

        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        if users_count < 0 or posts_count < 0 or comments_count < 0:
            raise CommandError("Cannot be negative")

        if clear:
            self.__clear_data()

        categories: list[Category]
        tags: list[Tag]
        categories, tags = self.__create_categories_and_tags()

        created_users_cnt: int = self.__create_users(users_count, fake)
        all_users: list[User] = list(User.objects.filter(is_superuser=False))

        if posts_count > 0 and not all_users:
            raise CommandError("There are no users")

        created_posts: list[Post] = self.__create_posts(
            posts_count, all_users, categories, tags, fake
        )
        published_posts: list[Post] = [
            post
            for post in created_posts
            if post.status == Post.StatusChoices.PUBLISHED
        ]
        if not published_posts:
            published_posts = list(
                Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
            )

        if comments_count > 0 and not published_posts:
            raise CommandError(
                "Comments were requested but no published posts exist."
            )

        created_comments_cnt: int = self.__create_comments(
            comments_count, all_users, published_posts, fake
        )

        time_spent: float = (datetime.now() - start_time).total_seconds()

        self.stdout.write(
            self.style.SUCCESS(f"Users: {created_users_cnt:>5} created")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Categories: {len(self.CATEGORIES):>5} created")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Tags: {len(self.TAGS):>5} created")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Posts: {len(created_posts):>5} created")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Comments: {created_comments_cnt:>5} created")
        )
        self.stdout.write(self.style.SUCCESS(f"Done in {time_spent:.2f} seconds"))