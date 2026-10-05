from django.contrib import admin
from django.core.handlers.wsgi import WSGIRequest
from django.utils.html import format_html
from django.utils.safestring import SafeString

from apps.auths.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
    ]
    list_filter = ["is_staff", "is_active"]
    readonly_fields = ["id"]
    search_fields = ["id", "email", "first_name", "last_name"]
    filter_horizontal = ["user_permissions"]
    list_per_page = 50
    list_display_links = ("id", "email")

    fieldsets = (
        (
            "General Information",
            {
                "fields": (
                    "id",
                    "email",
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    ("is_active", "is_staff"),
                    "user_permissions",
                )
            },
        ),
    )

    def get_readonly_fields(
        self, request: WSGIRequest, obj: User | None = None
    ) -> list[str]:
        if obj:
            return ["first_name", "last_name", "email", "password"] + list(
                self.readonly_fields
            )
        return list(self.readonly_fields)