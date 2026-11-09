from datetime import datetime
import random
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError, CommandParser
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

    CATEGORIES = [
        "Python",
        "Django",
        "DevOps",
        "C++",
        "Frontend",
        "Backend",
        "DataBase",
        "Machine",
    ]

    TAGS = [
        # Python
        "asyncio",
        "pytest",
        # Django
        "Django REST Framework",
        "Django ORM",
        # DevOps
        "Docker",
        "Kubernetes",
        "CI/CD Pipelines",
        # C++
        "Standard Template Library (STL)",
        "Smart Pointers",
        # Frontend
        "React.js",
        "Tailwind CSS",
        "TypeScript",
        # Backend
        "REST API Design",
        "GraphQL",
        "WebSockets",
        # DataBase
        "PostgreSQL",
        "Redis Caching",
        "MongoDB",
        # Machine
        "Scikit-Learn",
        "PyTorch",
    ]

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
        existing_categories = set(Category.objects.values_list("name", flat=True))
        new_categories = [
            Category(name=name, slug=slugify(name))
            for name in self.CATEGORIES
            if name not in existing_categories
        ]
        Category.objects.bulk_create(new_categories)

        existing_tags = set(Tag.objects.values_list("name", flat=True))
        new_tags = [
            Tag(name=name, slug=slugify(name))
            for name in self.TAGS
            if name not in existing_tags
        ]
        Tag.objects.bulk_create(new_tags)

        return list(Category.objects.all()), list(Tag.objects.all())

    def __create_users(self, count: int, fake: Faker) -> int:
        hashed_password = make_password(self.DEFAULT_PASSWORD)
        existing_emails = set(User.objects.values_list("email", flat=True))
        users_to_create: list[User] = []

        for _ in range(count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@gmail.com"

            suffix = 1
            while email in existing_emails:
                email = f"{first_name.lower()}.{last_name.lower()}{suffix}@gmail.com"
                suffix += 1
            existing_emails.add(email)

            # Проверяем наличие поля username у модели пользователя
            user_kwargs = {
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
        used_slug = set(Post.objects.values_list("slug", flat=True))
        posts_to_create: list[Post] = []
        created_slugs: list[str] = []

        for _ in range(count):
            title = fake.sentence().rstrip(".")
            base_slug = slugify(title)
            slug = base_slug

            suffix = 2
            while slug in used_slug:
                slug = f"{base_slug}-{suffix}"
                suffix += 1
            used_slug.add(slug)
            created_slugs.append(slug)

            author = random.choice(users)
            content_text = "\n\n".join(fake.paragraphs(nb=3))
            status = "published" if random.random() < 0.7 else "draft"
            category = (
                random.choice(categories)
                if random.random() > 0.1 and categories
                else None
            )

            post_kwargs = {
                "title": title,
                "slug": slug,
                "category": category,
            }
            
            # Accommodate author/user field variations
            if hasattr(Post, "author"):
                post_kwargs["author"] = author
            elif hasattr(Post, "user"):
                post_kwargs["user"] = author

            # Accommodate content/body field variations
            if hasattr(Post, "content"):
                post_kwargs["content"] = content_text
            elif hasattr(Post, "body"):
                post_kwargs["body"] = content_text

            # Accommodate status field variations
            if hasattr(Post, "status"):
                post_kwargs["status"] = status

            posts_to_create.append(Post(**post_kwargs))

        Post.objects.bulk_create(posts_to_create)

        # Retrieve saved instances from DB to get primary keys for ManyToMany relationship
        saved_posts = list(Post.objects.filter(slug__in=created_slugs))

        if tags and saved_posts:
            for post in saved_posts:
                if hasattr(post, "tags"):
                    tag_count = random.randint(0, min(5, len(tags)))
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
        for _ in range(count):
            author = random.choice(users)
            post = random.choice(published_posts)
            comment_text = " ".join(fake.sentences(nb=random.randint(1, 3)))
            
            comment_kwargs = {"post": post}
            
            if hasattr(Comment, "author"):
                comment_kwargs["author"] = author
            elif hasattr(Comment, "user"):
                comment_kwargs["user"] = author
            elif hasattr(Comment, "author_name"):
                comment_kwargs["author_name"] = author.get_full_name() or author.username

            if hasattr(Comment, "content"):
                comment_kwargs["content"] = comment_text
            elif hasattr(Comment, "body"):
                comment_kwargs["body"] = comment_text

            comments_to_create.append(Comment(**comment_kwargs))

        Comment.objects.bulk_create(comments_to_create)
        return len(comments_to_create)

    def handle(self, *args: tuple[Any, ...], **options: dict[str, Any]) -> None:
        start_time: datetime = datetime.now()
        fake = Faker()

        users_count: int = options["users"]
        posts_count: int = options["posts"]
        comments_count: int = options["comments"]
        clear: bool = options["clear"]

        if users_count < 0 or posts_count < 0 or comments_count < 0:
            raise CommandError("Cannot be negative")

        if clear:
            self.__clear_data()

        categories, tags = self.__create_categories_and_tags()
        created_users_cnt = self.__create_users(users_count, fake)
        all_users = list(User.objects.filter(is_superuser=False))

        if posts_count > 0 and not all_users:
            raise CommandError("There are no users")

        created_posts = self.__create_posts(posts_count, all_users, categories, tags, fake)
        
        if hasattr(Post, "status"):
            published_posts = list(Post.objects.filter(status="published"))
        else:
            published_posts = created_posts

        if comments_count > 0 and not published_posts:
            raise CommandError("Comments were requested but no published posts exist.")

        created_comments_cnt = self.__create_comments(comments_count, all_users, published_posts, fake)

        time_spent = (datetime.now() - start_time).total_seconds()

        self.stdout.write(self.style.SUCCESS(f"Users:      {created_users_cnt:>5} created"))
        self.stdout.write(self.style.SUCCESS(f"Categories: {len(self.CATEGORIES):>5} created"))
        self.stdout.write(self.style.SUCCESS(f"Tags:       {len(self.TAGS):>5} created"))
        self.stdout.write(self.style.SUCCESS(f"Posts:      {len(created_posts):>5} created"))
        self.stdout.write(self.style.SUCCESS(f"Comments:   {created_comments_cnt:>5} created"))
        self.stdout.write(self.style.SUCCESS(f"Done in {time_spent:.2f} seconds"))