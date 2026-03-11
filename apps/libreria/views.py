from django.shortcuts import render
from django.conf import settings
from apps.layouts.models import UserLayout


def importar_imagen(request):
    import os
    recorte_url = None
    recorte = request.GET.get('recorte')
    if recorte:
        recorte_url = settings.MEDIA_URL + recorte

    clan_dir = os.path.join(settings.BASE_DIR, 'static', 'clan_symbols')
    clanes = []
    if os.path.exists(clan_dir):
        clanes = [f for f in os.listdir(clan_dir) if f.endswith('.png')]
        clanes.sort()

    path_dir = os.path.join(settings.BASE_DIR, 'static', 'path')
    sendas = []
    if os.path.exists(path_dir):
        sendas = [f for f in os.listdir(path_dir) if f.endswith('.png')]
        sendas.sort()

    icons_dir = os.path.join(settings.BASE_DIR, 'static', 'icons')
    libreria_icons = []
    if os.path.exists(icons_dir):
        libreria_icons = [f for f in os.listdir(icons_dir) if f.endswith('.png')]
        libreria_icons.sort()

    layout_options = []
    active_layout_id = None
    if request.user.is_authenticated:
        user_layouts = UserLayout.objects.filter(
            user=request.user,
            card_type='libreria',
        ).order_by('name', 'id')
        layout_options = [
            {'id': layout.id, 'name': layout.name, 'is_default': layout.is_default}
            for layout in user_layouts
        ]
        default_layout = next((layout for layout in layout_options if layout['is_default']), None)
        if default_layout:
            active_layout_id = default_layout['id']
        elif layout_options:
            active_layout_id = layout_options[0]['id']

    return render(request, 'cripta/importar_imagen.html', {
        'imagen_url': recorte_url,
        'clanes': clanes,
        'sendas': sendas,
        'libreria_icons': libreria_icons,
        'layout_options': layout_options,
        'active_layout_id': active_layout_id,
        'card_type': 'libreria',
    })
