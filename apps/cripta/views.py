from django.shortcuts import render
from django.conf import settings
from apps.layouts.models import UserLayout

# Vista para importar imagen y mostrarla


def importar_imagen(request):
    import os

    recorte_url = None
    recorte = request.GET.get("recorte")
    if recorte:
        recorte_url = settings.MEDIA_URL + recorte

    # Obtener lista de archivos PNG de clanes
    clan_dir = os.path.join(settings.BASE_DIR, "static", "clan_symbols")
    clanes = []
    if os.path.exists(clan_dir):
        clanes = [f for f in os.listdir(clan_dir) if f.endswith(".png")]
        clanes.sort()

    # Obtener lista de archivos PNG de sendas/path
    path_dir = os.path.join(settings.BASE_DIR, "static", "path")
    sendas = []
    if os.path.exists(path_dir):
        sendas = [f for f in os.listdir(path_dir) if f.endswith(".png")]
        sendas.sort()

    layout_options = []
    active_layout_id = None
    if request.user.is_authenticated:
        user_layouts = UserLayout.objects.filter(
            user=request.user,
            card_type="cripta",
        ).order_by("name", "id")
        layout_options = [
            {"id": layout.id, "name": layout.name, "is_default": layout.is_default}
            for layout in user_layouts
        ]
        default_layout = next((layout for layout in layout_options if layout["is_default"]), None)
        if default_layout:
            active_layout_id = default_layout["id"]
        elif layout_options:
            active_layout_id = layout_options[0]["id"]

    return render(
        request,
        "cripta/importar_imagen.html",
        {
            "imagen_url": recorte_url,
            "clanes": clanes,
            "sendas": sendas,
            "layout_options": layout_options,
            "active_layout_id": active_layout_id,
            "card_type": "cripta",
        },
    )
