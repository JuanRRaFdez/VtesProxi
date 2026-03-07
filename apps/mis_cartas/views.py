import os
import io
import json
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from urllib.parse import urlencode
from .pdf_service import generate_pdf_bytes, validate_layout_params


def _list_user_cards(username, query_norm):
    cartas_dir = os.path.join(settings.MEDIA_ROOT, 'cartas', username)
    cartas = []
    if os.path.exists(cartas_dir):
        for fname in os.listdir(cartas_dir):
            if not fname.lower().endswith('.png'):
                continue
            nombre_sin_ext = os.path.splitext(fname)[0]
            if query_norm and query_norm not in nombre_sin_ext.lower():
                continue
            fpath = os.path.join(cartas_dir, fname)
            mtime = os.path.getmtime(fpath)
            fecha = datetime.fromtimestamp(mtime).strftime('%d/%m/%Y %H:%M')
            url = settings.MEDIA_URL + f'cartas/{username}/{fname}'
            cartas.append({'url': url, 'fecha': fecha, 'nombre': fname, 'mtime': mtime})
    cartas.sort(key=lambda c: c['mtime'], reverse=True)
    return cartas


@login_required
def mis_cartas(request):
    """Muestra todas las cartas guardadas del usuario autenticado."""
    username = request.user.username
    query = (request.GET.get('q') or '').strip().lower()
    page_number = request.GET.get('page')
    cartas = _list_user_cards(username, query)
    paginator = Paginator(cartas, 60)
    page_obj = paginator.get_page(page_number)

    return render(request, 'mis_cartas/mis_cartas.html', {
        'cartas': page_obj.object_list,
        'query': query,
        'page_obj': page_obj,
    })


@login_required
def pdf_workspace(request):
    username = request.user.username
    query = (request.GET.get('q') or '').strip().lower()
    cartas = _list_user_cards(username, query)
    return render(
        request,
        'mis_cartas/pdf_workspace.html',
        {
            'cartas': cartas,
            'query': query,
        },
    )


def _resolve_user_card_path(username, filename):
    if not filename or os.path.basename(filename) != filename:
        raise Http404('Archivo inválido')
    if not filename.lower().endswith('.png'):
        raise Http404('Formato no permitido')
    card_path = os.path.join(settings.MEDIA_ROOT, 'cartas', username, filename)
    if not os.path.exists(card_path):
        raise Http404('Archivo no encontrado')
    return card_path


@login_required
def descargar_carta(request, filename):
    username = request.user.username
    card_path = _resolve_user_card_path(username, filename)
    return FileResponse(open(card_path, 'rb'), as_attachment=True, filename=filename)


@login_required
def borrar_carta(request, filename):
    if request.method != 'POST':
        raise Http404('Método no permitido')

    username = request.user.username
    card_path = _resolve_user_card_path(username, filename)
    try:
        os.remove(card_path)
    except Exception:
        pass

    query = (request.POST.get('q') or '').strip().lower()
    page = (request.POST.get('page') or '').strip()
    params = {}
    if query:
        params['q'] = query
    if page:
        params['page'] = page
    url = '/mis-cartas/'
    if params:
        url = f"{url}?{urlencode(params)}"
    return redirect(url)


@login_required
def generar_pdf_cartas(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    data = json.loads(request.body.decode('utf-8') or '{}')
    width_mm = float(data.get('width_mm', 63))
    height_mm = float(data.get('height_mm', 88))
    items = data.get('items') or []
    selected = data.get('selected') or []
    copies = int(data.get('copies', 1))

    username = request.user.username
    selected_paths = []

    if items:
        for item in items:
            if not isinstance(item, dict):
                return JsonResponse({'error': 'Formato de items inválido'}, status=400)
            filename = item.get('filename')
            quantity = item.get('quantity')
            try:
                quantity = int(quantity)
            except (TypeError, ValueError):
                return JsonResponse({'error': 'La cantidad por carta debe ser un entero'}, status=400)
            if quantity <= 0:
                return JsonResponse({'error': 'La cantidad por carta debe ser mayor que 0'}, status=400)
            card_path = _resolve_user_card_path(username, filename)
            selected_paths.extend([card_path] * quantity)
        effective_copies = 1
    else:
        if not selected:
            return JsonResponse({'error': 'Debes seleccionar al menos una carta'}, status=400)
        selected_paths = [_resolve_user_card_path(username, fname) for fname in selected]
        effective_copies = copies

    try:
        validate_layout_params(width_mm, height_mm, effective_copies)
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    pdf_bytes = generate_pdf_bytes(
        selected_paths,
        width_mm=width_mm,
        height_mm=height_mm,
        copies=effective_copies,
        cut_marks=True,
    )
    pdf_stream = io.BytesIO(pdf_bytes)
    return FileResponse(
        pdf_stream,
        as_attachment=True,
        filename=f"cartas_{username}.pdf",
        content_type='application/pdf',
    )
