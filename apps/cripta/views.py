from django.shortcuts import redirect, render
import requests
from django.conf import settings

# Vista para importar imagen y mostrarla

def importar_imagen(request):
    import os
    recorte_url = None
    recorte = request.GET.get('recorte')
    if recorte:
        recorte_url = settings.MEDIA_URL + recorte

    # Obtener lista de archivos PNG de clanes
    clan_dir = os.path.join(settings.BASE_DIR, 'static', 'clan_symbols')
    clanes = []
    if os.path.exists(clan_dir):
        clanes = [f for f in os.listdir(clan_dir) if f.endswith('.png')]
        clanes.sort()

    # Obtener lista de archivos PNG de sendas/path
    path_dir = os.path.join(settings.BASE_DIR, 'static', 'path')
    sendas = []
    if os.path.exists(path_dir):
        sendas = [f for f in os.listdir(path_dir) if f.endswith('.png')]
        sendas.sort()

    return render(request, 'cripta/importar_imagen.html', {
        'imagen_url': recorte_url,
        'clanes': clanes,
        'sendas': sendas,
    })
