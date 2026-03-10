from django.conf import settings
from django.db import models
from django.db.models import Q


class UserLayout(models.Model):
    CARD_TYPE_CHOICES = [
        ('cripta', 'cripta'),
        ('libreria', 'libreria'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    card_type = models.CharField(max_length=16, choices=CARD_TYPE_CHOICES)
    config = models.JSONField(default=dict)
    is_default = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'card_type', 'name'],
                name='layouts_unique_name_per_user_card_type',
            ),
            models.UniqueConstraint(
                fields=['user', 'card_type'],
                condition=Q(is_default=True),
                name='layouts_one_default_per_user_card_type',
            ),
        ]
