from django.shortcuts import render
from django.conf import settings


def importar_imagen(request):
    import os
    import json
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

    layouts_json_path = os.path.join(settings.BASE_DIR, 'apps', 'srv_textos', 'layouts.json')
    layout_options = []
    active_layout = ''
    if os.path.exists(layouts_json_path):
        with open(layouts_json_path, encoding='utf-8') as f:
            layouts_data = json.load(f)
        layout_options = sorted(list((layouts_data.get('layouts') or {}).keys()))
        active_layout = layouts_data.get('active', '')

    return render(request, 'cripta/importar_imagen.html', {
        'imagen_url': recorte_url,
        'clanes': clanes,
        'sendas': sendas,
        'libreria_icons': libreria_icons,
        'layout_options': layout_options,
        'active_layout': active_layout,
        'card_type': 'libreria',
    })
