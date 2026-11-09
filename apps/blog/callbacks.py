import json
import os
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import HttpRequest

from apps.blog.models import Category, Comment, Post

User = get_user_model()


def environment_callback(request: HttpRequest) -> list[str]:
    env = os.environ.get("BLOG_ENV_ID", "local").lower()
    if env == "production":
        return ["Production", "danger"]
    return ["Local", "warning"]


def drafts_badge(request: HttpRequest) -> str:
    """Returns the count of draft posts as a string for the sidebar badge."""
    return str(Post.objects.filter(status="draft").count())


def dashboard_callback(request: HttpRequest, context: dict[str, Any]) -> dict[str, Any]:
    """Populates context data for the admin dashboard index page."""
    total_users = User.objects.count()
    total_comments = Comment.objects.count()
    published_posts = Post.objects.filter(status="published").count()
    draft_posts = Post.objects.filter(status="draft").count()
    total_posts = published_posts + draft_posts

    category_counts = Category.objects.annotate(post_count=Count("posts")).values("name", "post_count")
    cat_labels = [c["name"] for c in category_counts]
    cat_data = [c["post_count"] for c in category_counts]

    chart_data = {
        "labels": cat_labels,
        "datasets": [
            {
                "label": "Posts per Category",
                "data": cat_data,
                "backgroundColor": "#6366f1",
            }
        ],
    }

    top_authors = User.objects.annotate(post_count=Count("posts")).order_by("-post_count")[:5]
    authors_table = [
        {
            "name": f"{author.first_name} {author.last_name}".strip() or author.email,
            "email": author.email,
            "posts": author.post_count,
        }
        for author in top_authors
    ]

    published_share = round((published_posts / total_posts * 100), 1) if total_posts > 0 else 0
    draft_share = round((draft_posts / total_posts * 100), 1) if total_posts > 0 else 0

    context.update(
        {
            "kpi_users": total_users,
            "kpi_published": published_posts,
            "kpi_drafts": draft_posts,
            "kpi_comments": total_comments,
            "chart_data_json": json.dumps(chart_data),
            "top_authors": authors_table,
            "published_share": published_share,
            "draft_share": draft_share,
        }
    )
    return context