import json

from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.layouts.models import UserLayout
from apps.layouts.services import LayoutValidationError, load_classic_seed, validate_layout_config


@login_required
def editor(request):
    card_type = (request.GET.get('card_type') or 'cripta').strip().lower()
    if card_type not in ('cripta', 'libreria'):
        card_type = 'cripta'

    layouts = list(
        UserLayout.objects.filter(user=request.user, card_type=card_type).order_by('name', 'id')
    )
    active_layout = next((layout for layout in layouts if layout.is_default), None)
    if active_layout is None and layouts:
        active_layout = layouts[0]

    context = {
        'initial_card_type': card_type,
        'initial_layouts': [_serialize_layout(layout) for layout in layouts],
        'active_layout_id': active_layout.id if active_layout else None,
    }
    return render(request, 'layouts/editor.html', context)


def _serialize_layout(layout):
    return {
        'id': layout.id,
        'name': layout.name,
        'card_type': layout.card_type,
        'config': layout.config,
        'is_default': layout.is_default,
    }


def _get_payload(request):
    if request.content_type and 'application/json' in request.content_type:
        try:
            return json.loads(request.body.decode('utf-8') or '{}')
        except json.JSONDecodeError:
            return None
    return request.POST


@login_required
def api_list(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    card_type = (request.GET.get('card_type') or '').strip().lower()
    layouts = UserLayout.objects.filter(user=request.user)
    if card_type:
        layouts = layouts.filter(card_type=card_type)

    payload = [_serialize_layout(layout) for layout in layouts.order_by('name')]
    return JsonResponse({'layouts': payload})


@login_required
def api_create(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    payload = _get_payload(request)
    if payload is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    name = (payload.get('name') or '').strip()
    card_type = (payload.get('card_type') or '').strip().lower()
    if not name:
        return JsonResponse({'error': 'name es obligatorio'}, status=400)
    if card_type not in ('cripta', 'libreria'):
        return JsonResponse({'error': 'card_type inválido'}, status=400)

    try:
        layout = UserLayout.objects.create(
            user=request.user,
            name=name,
            card_type=card_type,
            config=load_classic_seed(card_type),
            is_default=False,
        )
    except IntegrityError:
        return JsonResponse({'error': 'Nombre de layout duplicado'}, status=400)

    return JsonResponse({'layout': _serialize_layout(layout)}, status=201)


@login_required
def api_detail(request, layout_id):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    layout = get_object_or_404(UserLayout, id=layout_id, user=request.user)
    return JsonResponse({'layout': _serialize_layout(layout)})


@login_required
def api_update_config(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    payload = _get_payload(request)
    if payload is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    layout_id = payload.get('layout_id')
    config = payload.get('config')
    if not layout_id:
        return JsonResponse({'error': 'layout_id es obligatorio'}, status=400)
    if config is None:
        return JsonResponse({'error': 'config es obligatorio'}, status=400)

    layout = get_object_or_404(UserLayout, id=layout_id, user=request.user)
    try:
        layout.config = validate_layout_config(layout.card_type, config)
    except LayoutValidationError as exc:
        return JsonResponse({'error': str(exc)}, status=400)

    layout.save(update_fields=['config'])
    return JsonResponse({'layout': _serialize_layout(layout)})


@login_required
def api_rename(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    payload = _get_payload(request)
    if payload is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    layout_id = payload.get('layout_id')
    name = (payload.get('name') or '').strip()
    if not layout_id:
        return JsonResponse({'error': 'layout_id es obligatorio'}, status=400)
    if not name:
        return JsonResponse({'error': 'name es obligatorio'}, status=400)

    layout = get_object_or_404(UserLayout, id=layout_id, user=request.user)
    layout.name = name
    try:
        layout.save(update_fields=['name'])
    except IntegrityError:
        return JsonResponse({'error': 'Nombre de layout duplicado'}, status=400)

    return JsonResponse({'layout': _serialize_layout(layout)})


@login_required
def api_delete(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    payload = _get_payload(request)
    if payload is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    layout_id = payload.get('layout_id')
    if not layout_id:
        return JsonResponse({'error': 'layout_id es obligatorio'}, status=400)

    layout = get_object_or_404(UserLayout, id=layout_id, user=request.user)
    layout.delete()
    return JsonResponse({'ok': True})


@login_required
def api_set_default(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    payload = _get_payload(request)
    if payload is None:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    layout_id = payload.get('layout_id')
    if not layout_id:
        return JsonResponse({'error': 'layout_id es obligatorio'}, status=400)

    layout = get_object_or_404(UserLayout, id=layout_id, user=request.user)

    with transaction.atomic():
        UserLayout.objects.filter(
            user=request.user,
            card_type=layout.card_type,
            is_default=True,
        ).exclude(id=layout.id).update(is_default=False)
        layout.is_default = True
        layout.save(update_fields=['is_default'])

    return JsonResponse({'layout': _serialize_layout(layout)})
