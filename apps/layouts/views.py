from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from apps.layouts.models import UserLayout
from apps.layouts.services import load_classic_seed


@login_required
def editor(request):
    return render(request, 'layouts/editor.html')


def _serialize_layout(layout):
    return {
        'id': layout.id,
        'name': layout.name,
        'card_type': layout.card_type,
        'config': layout.config,
        'is_default': layout.is_default,
    }


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

    name = (request.POST.get('name') or '').strip()
    card_type = (request.POST.get('card_type') or '').strip().lower()
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
