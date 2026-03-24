import os
from datetime import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings


@login_required
def mis_cartas(request):
    """Muestra todas las cartas guardadas del usuario autenticado."""
    username = request.user.username
    cartas_dir = os.path.join(settings.MEDIA_ROOT, "cartas", username)
    cartas = []
    if os.path.exists(cartas_dir):
        for fname in sorted(os.listdir(cartas_dir), reverse=True):
            if fname.lower().endswith(".png"):
                fpath = os.path.join(cartas_dir, fname)
                mtime = os.path.getmtime(fpath)
                fecha = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
                url = settings.MEDIA_URL + f"cartas/{username}/{fname}"
                cartas.append({"url": url, "fecha": fecha, "nombre": fname})
    return render(request, "usuarios/mis_cartas.html", {"cartas": cartas})
