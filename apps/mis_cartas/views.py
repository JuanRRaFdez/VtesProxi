import os
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from urllib.parse import urlencode


def _list_user_cards(username, query_norm):
    cartas_dir = os.path.join(settings.MEDIA_ROOT, "cartas", username)
    cartas = []
    if os.path.exists(cartas_dir):
        for fname in os.listdir(cartas_dir):
            if not fname.lower().endswith(".png"):
                continue
            nombre_sin_ext = os.path.splitext(fname)[0]
            if query_norm and query_norm not in nombre_sin_ext.lower():
                continue
            fpath = os.path.join(cartas_dir, fname)
            mtime = os.path.getmtime(fpath)
            fecha = datetime.fromtimestamp(mtime).strftime("%d/%m/%Y %H:%M")
            url = settings.MEDIA_URL + f"cartas/{username}/{fname}"
            cartas.append({"url": url, "fecha": fecha, "nombre": fname, "mtime": mtime})
    cartas.sort(key=lambda c: c["mtime"], reverse=True)
    return cartas


@login_required
def mis_cartas(request):
    """Muestra todas las cartas guardadas del usuario autenticado."""
    username = request.user.username
    query = (request.GET.get("q") or "").strip().lower()
    page_number = request.GET.get("page")
    cartas = _list_user_cards(username, query)
    paginator = Paginator(cartas, 60)
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "mis_cartas/mis_cartas.html",
        {
            "cartas": page_obj.object_list,
            "query": query,
            "page_obj": page_obj,
        },
    )


def _resolve_user_card_path(username, filename):
    if not filename or os.path.basename(filename) != filename:
        raise Http404("Archivo inválido")
    if not filename.lower().endswith(".png"):
        raise Http404("Formato no permitido")
    card_path = os.path.join(settings.MEDIA_ROOT, "cartas", username, filename)
    if not os.path.exists(card_path):
        raise Http404("Archivo no encontrado")
    return card_path


@login_required
def descargar_carta(request, filename):
    username = request.user.username
    card_path = _resolve_user_card_path(username, filename)
    return FileResponse(open(card_path, "rb"), as_attachment=True, filename=filename)


@login_required
def borrar_carta(request, filename):
    if request.method != "POST":
        raise Http404("Método no permitido")

    username = request.user.username
    card_path = _resolve_user_card_path(username, filename)
    try:
        os.remove(card_path)
    except Exception:
        pass

    query = (request.POST.get("q") or "").strip().lower()
    page = (request.POST.get("page") or "").strip()
    params = {}
    if query:
        params["q"] = query
    if page:
        params["page"] = page
    url = "/mis-cartas/"
    if params:
        url = f"{url}?{urlencode(params)}"
    return redirect(url)

