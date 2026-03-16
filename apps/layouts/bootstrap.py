from apps.layouts.models import UserLayout
from apps.layouts.services import load_classic_seed, validate_layout_config


DEFAULT_LAYOUT_NAME = 'classic'
DEFAULT_CARD_TYPES = ('cripta', 'libreria')


def ensure_default_layouts_for_user(user):
    if not user or not getattr(user, 'pk', None):
        return

    for card_type in DEFAULT_CARD_TYPES:
        default_layout = UserLayout.objects.filter(
            user=user,
            card_type=card_type,
            is_default=True,
        ).first()
        if default_layout:
            continue

        classic_layout = UserLayout.objects.filter(
            user=user,
            card_type=card_type,
            name=DEFAULT_LAYOUT_NAME,
        ).first()
        if classic_layout:
            if not classic_layout.is_default:
                classic_layout.is_default = True
                classic_layout.save(update_fields=['is_default'])
            continue

        UserLayout.objects.create(
            user=user,
            name=DEFAULT_LAYOUT_NAME,
            card_type=card_type,
            config=validate_layout_config(card_type, load_classic_seed(card_type)),
            is_default=True,
        )
