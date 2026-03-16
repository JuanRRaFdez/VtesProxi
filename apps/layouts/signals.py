from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.layouts.bootstrap import ensure_default_layouts_for_user


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_layouts_for_new_user(sender, instance, created, **kwargs):
    if not created:
        return

    ensure_default_layouts_for_user(instance)
