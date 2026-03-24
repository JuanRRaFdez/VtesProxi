from django.apps import AppConfig


class LayoutsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.layouts"

    def ready(self):
        from apps.layouts import signals  # noqa: F401
