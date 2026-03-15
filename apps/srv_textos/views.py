from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from copy import deepcopy
import os
import json
import shutil
import re
from PIL import Image, ImageDraw, ImageFont
from django.utils.crypto import get_random_string
from apps.layouts.services import (
    LayoutOwnershipError,
    LayoutValidationError,
    get_user_layout_config,
    normalize_layout_config,
    validate_layout_config,
)
from .card_catalog import search_card_suggestions, get_card_autocomplete


def _load_layout(layout_name=None):
    """Carga un layout concreto (si se indica) o el activo desde layouts.json."""
    json_path = os.path.join(os.path.dirname(__file__), 'layouts.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    active = data.get('active')
    selected = (layout_name or '').strip() or active
    layout = data['layouts'].get(selected)
    if layout is None:
        raise KeyError(f"Layout '{selected}' no encontrado en layouts.json")
    return layout


def _normalize_card_type(card_type):
    normalized = (card_type or 'cripta').strip().lower()
    if normalized not in ('cripta', 'libreria'):
        return 'cripta'
    return normalized


def _resolve_layout_config(request_user, card_type, layout_id=None, layout_name=None, layout_override=None):
    normalized_card_type = _normalize_card_type(card_type)

    if layout_override is not None:
        return validate_layout_config(normalized_card_type, layout_override)

    normalized_layout_id = layout_id
    if isinstance(normalized_layout_id, str):
        normalized_layout_id = normalized_layout_id.strip()
        if not normalized_layout_id:
            normalized_layout_id = None

    if normalized_layout_id is not None:
        try:
            normalized_layout_id = int(normalized_layout_id)
        except (TypeError, ValueError) as exc:
            raise LayoutValidationError('layout_id inválido') from exc

        selected = get_user_layout_config(
            request_user=request_user,
            card_type=normalized_card_type,
            layout_id=normalized_layout_id,
        )
        if selected is None:
            raise LayoutValidationError('layout_id no existe')
        return selected

    default_layout = get_user_layout_config(
        request_user=request_user,
        card_type=normalized_card_type,
    )
    if default_layout is not None:
        return default_layout

    try:
        return _load_layout(layout_name)
    except KeyError as exc:
        raise LayoutValidationError(str(exc)) from exc


def _safe_card_filename_base(nombre):
    base = (nombre or '').strip()
    if not base:
        return ''
    base = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', base)
    base = re.sub(r'\s+', ' ', base).strip().strip('.')
    base = base.lower()
    return base


# --- Helper: abre un símbolo (PNG o SVG) y lo redimensiona ---
def _load_symbol(symbol_path, size):
    if symbol_path.lower().endswith('.svg'):
        import cairosvg
        from io import BytesIO
        png_bytes = cairosvg.svg2png(url=symbol_path, output_width=size, output_height=size)
        return Image.open(BytesIO(png_bytes)).convert('RGBA')
    else:
        img = Image.open(symbol_path).convert('RGBA')
        return img.resize((size, size), Image.LANCZOS)


# --- Helper: resuelve la ruta de la imagen base ---
def _resolve_imagen_path(imagen_url):
    imagen_path = imagen_url
    if imagen_url.startswith(settings.MEDIA_URL):
        imagen_path = imagen_url.replace(settings.MEDIA_URL, '')
    if '/render/' in imagen_path:
        imagen_path = imagen_url.replace(settings.MEDIA_URL, '').replace(
            'render/', 'recortes/').replace('render_', 'recorte_')
    return os.path.join(settings.MEDIA_ROOT, imagen_path)


def _prepare_render_source_from_path(imagen_abspath, target_name=None):
    if not imagen_abspath or not os.path.exists(imagen_abspath):
        return None

    preview_dir = os.path.join(settings.MEDIA_ROOT, 'layout_preview_sources')
    os.makedirs(preview_dir, exist_ok=True)

    source_ext = os.path.splitext(imagen_abspath)[1] or '.png'
    source_name = target_name or os.path.basename(imagen_abspath)
    safe_base = _safe_card_filename_base(source_name) or 'layout-preview'
    target_filename = safe_base + source_ext.lower()
    target_path = os.path.join(preview_dir, target_filename)

    shutil.copyfile(imagen_abspath, target_path)
    return settings.MEDIA_URL + 'layout_preview_sources/' + target_filename


def _resolve_font_path(font_path):
    if not font_path:
        raise ValueError('font_path requerido')
    if os.path.isabs(font_path):
        return font_path
    return os.path.join(settings.BASE_DIR, font_path)


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


def _measure_text_width(font, text):
    bbox = font.getbbox(text or '')
    return bbox[2] - bbox[0]


def _fit_text_to_box(text, font_path, start_font_size, min_font_size, max_width, ellipsis_enabled=True):
    safe_text = str(text or '')
    max_width = max(1, int(max_width))
    start_size = max(1, int(start_font_size))
    min_size = max(1, int(min_font_size))
    if start_size < min_size:
        start_size = min_size

    resolved_font_path = _resolve_font_path(font_path)

    for font_size in range(start_size, min_size - 1, -1):
        font = ImageFont.truetype(resolved_font_path, font_size)
        width = _measure_text_width(font, safe_text)
        if width <= max_width:
            return {
                'text': safe_text,
                'font_size': font_size,
                'width': width,
                'font': font,
            }

    font = ImageFont.truetype(resolved_font_path, min_size)
    fitted_text = safe_text
    fitted_width = _measure_text_width(font, fitted_text)

    if ellipsis_enabled and safe_text:
        ellipsis = '...'
        trimmed = safe_text
        while trimmed:
            candidate = trimmed + ellipsis
            candidate_width = _measure_text_width(font, candidate)
            if candidate_width <= max_width:
                fitted_text = candidate
                fitted_width = candidate_width
                break
            trimmed = trimmed[:-1]

    return {
        'text': fitted_text,
        'font_size': min_size,
        'width': fitted_width,
        'font': font,
    }


def _compute_aligned_x(box_x, text_width, align, box_width=100):
    start_x = int(box_x)
    text_width = max(0, int(text_width))
    box_width = max(1, int(box_width))

    if align == 'right':
        return start_x + max(0, box_width - text_width)
    if align == 'center':
        return start_x + max(0, (box_width - text_width) // 2)
    return start_x


def _clamp_box(box, default_box):
    source = box if isinstance(box, dict) else {}
    return {
        'x': int(source.get('x', default_box['x'])),
        'y': int(source.get('y', default_box['y'])),
        'width': max(1, int(source.get('width', default_box['width']))),
        'height': max(1, int(source.get('height', default_box['height']))),
    }


def _compute_habilidad_dynamic_height(habilidad, font_size, max_width, line_spacing, padding):
    safe_text = str(habilidad or '').strip()
    usable_width = max(1, int(max_width) - max(0, int(padding * 2)))
    if not safe_text:
        return max(1, int(font_size + (padding * 2)))

    if usable_width <= 0:
        return max(1, int(font_size + (padding * 2)))

    approx_chars_per_line = max(1, int(usable_width / max(1, font_size * 0.55)))
    line_count = 0
    for block in safe_text.split('\n'):
        block = block.strip()
        if not block:
            line_count += 1
            continue
        wrapped = (len(block) + approx_chars_per_line - 1) // approx_chars_per_line
        line_count += max(1, wrapped)

    return int((line_count * (font_size + line_spacing)) + max(0, padding * 2))


def _compute_disc_metrics_from_box(box, icon_count):
    normalized_count = max(1, int(icon_count or 0))
    size = max(1, int(box['width']))
    spacing = max(1, int(box['height'] / normalized_count))
    return size, spacing


def _compute_symbol_metrics_from_box(box, icon_count):
    normalized_count = max(1, int(icon_count or 0))
    size_by_width = int(box['width'])
    size_by_height = int(box['height'] / normalized_count)
    size = max(1, min(size_by_width, size_by_height))
    spacing = max(1, int(box['height'] / normalized_count))
    return {'size': size, 'spacing': spacing}


def _get_classic_style_tokens(card_type):
    normalized_card_type = _normalize_card_type(card_type)
    classic = _load_layout('classic')
    classic_scope = classic.get('libreria', {}) if normalized_card_type == 'libreria' else classic
    classic_il = classic_scope.get('ilustrador') or classic.get('ilustrador') or {}
    classic_cripta = classic.get('cripta') or {}

    return {
        'ilustrador': {
            'font_size': int(classic_il.get('font_size', 24) or 24),
            'color': classic_il.get('color', 'white') or 'white',
        },
        'cripta': {
            'font_size': int(classic_cripta.get('font_size', 35) or 35),
            'color': classic_cripta.get('color', 'white') or 'white',
        },
    }


def _compute_vertical_stack_positions(box, item_size, spacing, item_count, source='legacy'):
    count = max(0, int(item_count or 0))
    if count == 0:
        return []

    item_size = max(1, int(item_size))
    spacing = max(1, int(spacing))

    positions = []
    if source == 'box':
        current_bottom = int(box.get('y', 0))
        for _ in range(count):
            current_y = current_bottom - item_size
            if current_y < 0:
                break
            positions.append(current_y)
            current_bottom -= spacing
        return positions

    top = int(box.get('y', 0))
    bottom = top + max(1, int(box.get('height', item_size)))
    current_y = bottom - item_size
    for _ in range(count):
        if current_y < top:
            break
        positions.append(current_y)
        current_y -= spacing
    return positions


def _boxes_overlap(box_a, box_b):
    if not box_a or not box_b:
        return False
    ax1 = box_a['x']
    ay1 = box_a['y']
    ax2 = ax1 + box_a['width']
    ay2 = ay1 + box_a['height']

    bx1 = box_b['x']
    by1 = box_b['y']
    bx2 = bx1 + box_b['width']
    by2 = by1 + box_b['height']

    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def _boxes_overlap_vertically(box_a, box_b):
    ay1 = box_a['y']
    ay2 = ay1 + box_a['height']
    by1 = box_b['y']
    by2 = by1 + box_b['height']
    return not (ay2 <= by1 or by2 <= ay1)


def _resolve_global_collisions(metrics, card_height):
    resolved = deepcopy(metrics)
    habilidad_metrics = resolved.get('habilidad', {})
    habilidad_box = habilidad_metrics.get('used_box') or habilidad_metrics.get('box')
    if not isinstance(habilidad_box, dict):
        return resolved

    priority = ['disciplinas', 'simbolos', 'coste', 'ilustrador']
    vertical_only = {'disciplinas', 'simbolos', 'coste'}
    for key in priority:
        section = resolved.get(key)
        if not isinstance(section, dict):
            continue
        box = section.get('box')
        if not isinstance(box, dict):
            continue

        anchor_mode = section.get('anchor_mode', 'free')
        if section.get('source') == 'box' and anchor_mode == 'free':
            continue
        if anchor_mode in ('bottom_locked', 'fixed_bottom'):
            continue

        min_y = 0
        max_y = max(0, int(card_height) - box['height'])
        if key in vertical_only:
            overlaps = _boxes_overlap_vertically
        else:
            overlaps = _boxes_overlap

        while overlaps(box, habilidad_box) and box['y'] > min_y:
            box['y'] -= 1

        if box['y'] > max_y:
            box['y'] = max_y
        if box['y'] < min_y:
            box['y'] = min_y

    return resolved


def _compute_layout_metrics(config, card_type='cripta', habilidad='', nombre='', ilustrador='', disciplinas=None, simbolos=None, dynamic_habilidad_from_bottom=False, hab_font_size=None):
    normalized_card_type = _normalize_card_type(card_type)
    raw_lay = config if isinstance(config, dict) else {}
    lay = normalize_layout_config(normalized_card_type, config)
    classic_styles = _get_classic_style_tokens(normalized_card_type)
    lc = lay['carta']
    card_w = int(lc['width'])
    card_h = int(lc['height'])

    layout_scope = lay.get('libreria', {}) if normalized_card_type == 'libreria' else lay
    raw_layout_scope = raw_lay.get('libreria', {}) if normalized_card_type == 'libreria' else raw_lay
    if not isinstance(raw_layout_scope, dict):
        raw_layout_scope = {}

    ln = layout_scope.get('nombre') or lay.get('nombre') or {}
    lil = layout_scope.get('ilustrador') or lay.get('ilustrador') or {}
    ld = layout_scope.get('disciplinas') or lay.get('disciplinas') or {}
    lsi = (layout_scope.get('simbolos') or lay.get('simbolos')) if normalized_card_type == 'libreria' else None
    lh = layout_scope.get('habilidad') or lay.get('habilidad') or {}
    lco = layout_scope.get('coste') or lay.get('coste') or {}
    lcr = lay.get('cripta') or {}

    raw_lil = raw_layout_scope.get('ilustrador') or raw_lay.get('ilustrador') or {}
    raw_ld = raw_layout_scope.get('disciplinas') or raw_lay.get('disciplinas') or {}
    raw_lsi = (raw_layout_scope.get('simbolos') or raw_lay.get('simbolos')) if normalized_card_type == 'libreria' else None
    raw_lh = raw_layout_scope.get('habilidad') or raw_lay.get('habilidad') or {}
    raw_lcr = raw_lay.get('cripta') or {}

    ln_y = ln.get('y', 0)
    if isinstance(ln_y, float):
        ln_default_y = int(card_h * ln_y)
    else:
        ln_default_y = int(ln_y or 0)

    nombre_box = _clamp_box(ln.get('box'), {
        'x': int(ln.get('x', 0) or 0),
        'y': ln_default_y,
        'width': card_w,
        'height': max(1, int(ln.get('font_size', 40) or 40)),
    })
    nombre_rules = ln.get('rules') if isinstance(ln.get('rules'), dict) else {}
    nombre_align = nombre_rules.get('align', 'left')
    nombre_fit = _fit_text_to_box(
        text=nombre,
        font_path=ln.get('font_path', 'static/fonts/MatrixExtraBold.otf'),
        start_font_size=ln.get('font_size', 40),
        min_font_size=nombre_rules.get('min_font_size', 18),
        max_width=nombre_box['width'],
        ellipsis_enabled=nombre_rules.get('ellipsis_enabled', True),
    )

    il_style = classic_styles['ilustrador']
    il_font_size = int(il_style['font_size'])
    il_box_default_y = max(0, card_h - int(lil.get('bottom', 0) or 0) - il_font_size)
    il_box = _clamp_box(lil.get('box'), {
        'x': int(lil.get('x', 45) or 45),
        'y': il_box_default_y,
        'width': max(1, card_w - 90),
        'height': max(1, il_font_size + 8),
    })
    il_rules = lil.get('rules') if isinstance(lil.get('rules'), dict) else {}
    il_align = il_rules.get('align', 'left')
    il_fit = _fit_text_to_box(
        text=ilustrador,
        font_path='static/fonts/Gill Sans.otf',
        start_font_size=il_font_size,
        min_font_size=il_font_size,
        max_width=il_box['width'],
        ellipsis_enabled=True,
    )

    layout_hab_font_size = int(lh.get('font_size', 33) or 33)
    hab_rules = lh.get('rules') if isinstance(lh.get('rules'), dict) else {}
    raw_hab_rules = raw_lh.get('rules') if isinstance(raw_lh.get('rules'), dict) else {}
    hab_vertical_padding = int(lh.get('bg_padding', 19) or 19)
    hab_default_y = int(card_h * float(lh.get('y_ratio', 0.83) or 0.83))
    hab_default_w = int(card_w * float(lh.get('max_width_ratio', 0.74) or 0.74))
    has_habilidad_box = isinstance(raw_lh.get('box'), dict)
    habilidad_box = _clamp_box(lh.get('box') if has_habilidad_box else None, {
        'x': int(lh.get('x', 160) or 160),
        'y': hab_default_y,
        'width': max(1, hab_default_w),
        'height': max(1, layout_hab_font_size),
    })

    is_dynamic_bottom_anchor = (
        bool(dynamic_habilidad_from_bottom)
        and normalized_card_type == 'cripta'
        and has_habilidad_box
    )
    raw_libreria_box_semantics = raw_hab_rules.get('box_semantics')
    is_libreria_bottom_anchor_margin = (
        normalized_card_type == 'libreria'
        and has_habilidad_box
        and raw_libreria_box_semantics == 'bottom_anchor_margin'
    )
    is_libreria_legacy_visual_box = (
        normalized_card_type == 'libreria'
        and has_habilidad_box
        and raw_libreria_box_semantics in {None, 'legacy'}
    )
    effective_hab_font_size = layout_hab_font_size
    if (is_dynamic_bottom_anchor or is_libreria_bottom_anchor_margin or is_libreria_legacy_visual_box) and hab_font_size is not None:
        effective_hab_font_size = max(20, min(int(hab_font_size), 80))

    dynamic_hab_box_h = _compute_habilidad_dynamic_height(
        habilidad=habilidad,
        font_size=effective_hab_font_size,
        max_width=habilidad_box['width'],
        line_spacing=int(lh.get('line_spacing', 4) or 4),
        padding=hab_vertical_padding,
    )
    dynamic_hab_content_h = max(1, int(dynamic_hab_box_h) - max(0, hab_vertical_padding * 2))

    if is_dynamic_bottom_anchor:
        hab_box_bottom = habilidad_box['y'] + habilidad_box['height']
        used_hab_box_y = max(0, hab_box_bottom - dynamic_hab_box_h)
        used_hab_box_h = max(1, hab_box_bottom - used_hab_box_y)
    elif is_libreria_legacy_visual_box:
        hab_box_bottom = habilidad_box['y'] + habilidad_box['height']
        # Legacy libreria boxes stored the full visual height. Preserve only the
        # inherited bottom edge and let the actual height respond to content.
        vertical_margin = max(0, int(hab_vertical_padding))
        outer_hab_box_h = max(1, dynamic_hab_content_h + (vertical_margin * 2))
        used_hab_box_y = max(0, hab_box_bottom - outer_hab_box_h)
        used_hab_box_h = max(1, hab_box_bottom - used_hab_box_y)
    elif is_libreria_bottom_anchor_margin:
        hab_box_bottom = habilidad_box['y']
        vertical_margin = max(0, int(habilidad_box['height']))
        outer_hab_box_h = max(1, dynamic_hab_content_h + (vertical_margin * 2))
        used_hab_box_y = max(0, hab_box_bottom - outer_hab_box_h)
        used_hab_box_h = max(1, hab_box_bottom - used_hab_box_y)
    elif has_habilidad_box:
        used_hab_box_h = min(habilidad_box['height'], dynamic_hab_box_h)
    else:
        fixed_hab_box_h = None
        if 'box_bottom_ratio' in lh:
            fixed_hab_box_h = int(card_h * float(lh['box_bottom_ratio'])) - habilidad_box['y']

        if fixed_hab_box_h is None or fixed_hab_box_h <= 0:
            habilidad_box['height'] = dynamic_hab_box_h
        else:
            habilidad_box['height'] = max(int(fixed_hab_box_h), int(dynamic_hab_box_h))
        used_hab_box_h = habilidad_box['height']

    used_hab_box = {
        'x': habilidad_box['x'],
        'y': used_hab_box_y if (is_dynamic_bottom_anchor or is_libreria_bottom_anchor_margin or is_libreria_legacy_visual_box) else habilidad_box['y'] + max(0, habilidad_box['height'] - used_hab_box_h),
        'width': habilidad_box['width'],
        'height': max(1, used_hab_box_h),
    }

    disc_rules = ld.get('rules') if isinstance(ld.get('rules'), dict) else {}
    disc_anchor_mode = disc_rules.get('anchor_mode', 'free')
    has_disc_box = isinstance(ld.get('box'), dict)
    disc_box = _clamp_box(ld.get('box') if has_disc_box and isinstance(ld, dict) else None, {
        'x': int(ld.get('x', 0) or 0) if isinstance(ld, dict) else 0,
        'y': max(0, card_h - int(ld.get('bottom', 100) or 100)) if isinstance(ld, dict) else 0,
        'width': int(ld.get('size', 64) or 64) if isinstance(ld, dict) else 64,
        'height': int(ld.get('spacing', 80) or 80) if isinstance(ld, dict) else 80,
    })
    if disc_anchor_mode == 'fixed_bottom':
        disc_box['y'] = max(0, int(disc_box['y']))
    else:
        gap_from_habilidad = max(0, int(disc_rules.get('gap_from_habilidad', 0) or 0))
        disc_box['y'] = max(0, used_hab_box['y'] - gap_from_habilidad)
    disc_size = max(1, int(disc_box['width']))
    disc_spacing = max(1, int(disc_box['height']))

    simbolos_box = None
    simbolos_metrics = None
    if normalized_card_type == 'libreria' and isinstance(lsi, dict):
        has_simbolos_box = isinstance((raw_lsi or {}).get('box'), dict)
        simbolos_box = _clamp_box(lsi.get('box') if has_simbolos_box else None, {
            'x': int(lsi.get('x', 0) or 0),
            'y': int(lsi.get('y', 0) or 0),
            'width': int(lsi.get('size', 64) or 64),
            'height': int((lsi.get('spacing', 80) or 80) * max(1, len(simbolos or []))),
        })
        simbolos_metrics = _compute_symbol_metrics_from_box(simbolos_box, icon_count=len(simbolos or []))
    else:
        has_simbolos_box = False

    has_ilustrador_box = isinstance(raw_lil.get('box'), dict)
    pad = int(lh.get('bg_padding', 19) or 19)
    has_cripta_box = isinstance(raw_lcr.get('box'), dict)
    cripta_style = classic_styles['cripta']
    cripta_font_size = int(cripta_style['font_size'])
    cripta_default_box = {
        'x': max(0, used_hab_box['x'] - pad),
        'y': max(0, used_hab_box['y'] - (pad * 2) - cripta_font_size - int(lcr.get('y_gap', 1) or 1)) if isinstance(lcr, dict) else 0,
        'width': max(30, cripta_font_size * 2),
        'height': max(30, cripta_font_size + 8),
    }
    cripta_box = _clamp_box(lcr.get('box') if has_cripta_box else None, cripta_default_box) if isinstance(lcr, dict) else None

    coste_size = int(lco.get('size', 64) or 64) if isinstance(lco, dict) else 64
    coste_bottom = int(lco.get('bottom', 40) or 40) if isinstance(lco, dict) else 40
    coste_x = int(lco.get('left', card_w - coste_size - int(lco.get('right', 40) or 40))) if isinstance(lco, dict) else card_w - coste_size - 40
    coste_box = {
        'x': max(0, coste_x),
        'y': max(0, card_h - coste_bottom - coste_size),
        'width': max(1, coste_size),
        'height': max(1, coste_size),
    }

    metrics = {
        'card': {'width': card_w, 'height': card_h},
        'nombre': {
            'box': nombre_box,
            'align': nombre_align,
            'shadow_enabled': bool((ln.get('shadow') or {}).get('enabled', False)),
            'fit': nombre_fit,
            'text_width': nombre_fit['width'],
        },
        'ilustrador': {
            'box': il_box,
            'align': il_align,
            'shadow_enabled': bool((lil.get('shadow') or {}).get('enabled', False)),
            'fit': il_fit,
            'style': il_style,
            'text_width': il_fit['width'],
            'anchor_mode': il_rules.get('anchor_mode', 'free'),
            'source': 'box' if has_ilustrador_box else 'legacy',
        },
        'habilidad': {
            'box': habilidad_box,
            'used_box': used_hab_box,
            'height': used_hab_box['height'],
            'source': 'box' if has_habilidad_box else 'legacy',
        },
        'disciplinas': {
            'box': disc_box,
            'size': disc_size,
            'spacing': disc_spacing,
            'anchor_mode': disc_anchor_mode if isinstance(ld, dict) else 'free',
            'source': 'box' if isinstance(ld, dict) and isinstance(ld.get('box'), dict) else 'legacy',
        },
        'coste': {
            'box': coste_box,
            'anchor_mode': 'bottom_locked',
        },
    }
    if cripta_box is not None:
        metrics['cripta'] = {
            'box': cripta_box,
            'style': cripta_style,
            'source': 'box' if has_cripta_box else 'legacy',
        }
    if simbolos_box is not None and simbolos_metrics is not None:
        metrics['simbolos'] = {
            'box': simbolos_box,
            'size': simbolos_metrics['size'],
            'spacing': simbolos_metrics['spacing'],
            'anchor_mode': ((lsi.get('rules') or {}).get('anchor_mode', 'free') if isinstance(lsi, dict) else 'free'),
            'source': 'box' if has_simbolos_box else 'legacy',
        }

    return _resolve_global_collisions(metrics, card_height=card_h)


# --- Helper: carga fuentes de habilidad ---
def _load_hab_fonts(size):
    fonts_dir = os.path.join(settings.BASE_DIR, 'static', 'fonts')
    bold_path = os.path.join(fonts_dir, 'Gill Sans Bold.otf')
    normal_path = os.path.join(fonts_dir, 'Gill Sans.otf')
    font_bold = ImageFont.truetype(bold_path, size)
    font_normal = ImageFont.truetype(normal_path, size)
    return font_bold, font_normal


# --- Helper: parsea texto de habilidad en segmentos con estilo ---
def _parse_habilidad(text):
    """
    Reglas de formato:
    1. Todo hasta los dos puntos ':' → bold
    2. Después de ':' hasta el primer '+' precedido por '.' → normal
         - Texto entre paréntesis '()' → italic
    3. Desde ese '+' en adelante → bold
    """
    segments = []
    if not text:
        return segments

    colon_idx = text.find(':')
    if colon_idx == -1:
        # Sin dos puntos: todo en bold
        return [{'text': text, 'style': 'bold'}]

    # Parte 1: hasta e incluyendo ':'
    segments.append({'text': text[:colon_idx + 1], 'style': 'bold'})

    rest = text[colon_idx + 1:]
    if not rest:
        return segments

    # Encontrar el primer '+' que venga precedido por '.' (ignorando espacios)
    plus_idx = None
    for i, ch in enumerate(rest):
        if ch != '+':
            continue
        j = i - 1
        while j >= 0 and rest[j].isspace():
            j -= 1
        if j >= 0 and rest[j] == '.':
            plus_idx = i
            break

    if plus_idx is not None:
        normal_section = rest[:plus_idx]
        bold_tail = rest[plus_idx:]
    else:
        normal_section = rest
        bold_tail = ''

    # Parsear sección normal buscando paréntesis (italic)
    _parse_normal_with_parens(normal_section, segments)

    if bold_tail.strip():
        segments.append({'text': bold_tail, 'style': 'bold'})

    return segments


def _parse_normal_with_parens(text, segments):
    """Divide texto normal en segmentos normal/italic según paréntesis."""
    i = 0
    while i < len(text):
        paren_start = text.find('(', i)
        if paren_start == -1:
            if i < len(text):
                segments.append({'text': text[i:], 'style': 'normal'})
            break
        # Texto antes del paréntesis
        if paren_start > i:
            segments.append({'text': text[i:paren_start], 'style': 'normal'})
        # Texto dentro del paréntesis (incluidos los paréntesis)
        paren_end = text.find(')', paren_start)
        if paren_end == -1:
            segments.append({'text': text[paren_start:], 'style': 'italic'})
            break
        segments.append({'text': text[paren_start:paren_end + 1], 'style': 'italic'})
        i = paren_end + 1


def _parse_libreria_habilidad(text):
    """
    Librería:
    - Texto entre ** ** -> bold
    - Resto -> normal
    """
    if not text:
        return []

    segments = []
    idx = 0
    is_bold = False
    while idx < len(text):
        marker = text.find('**', idx)
        if marker == -1:
            chunk = text[idx:]
            if chunk:
                segments.append({'text': chunk, 'style': 'bold' if is_bold else 'normal'})
            break

        chunk = text[idx:marker]
        if chunk:
            segments.append({'text': chunk, 'style': 'bold' if is_bold else 'normal'})
        is_bold = not is_bold
        idx = marker + 2

    return segments


def _split_parentheses_italic(text):
    """Divide un texto en fragmentos normal/cursiva según paréntesis."""
    spans = []
    i = 0
    while i < len(text):
        paren_start = text.find('(', i)
        if paren_start == -1:
            if i < len(text):
                spans.append({'text': text[i:], 'italic': False})
            break

        if paren_start > i:
            spans.append({'text': text[i:paren_start], 'italic': False})

        paren_end = text.find(')', paren_start)
        if paren_end == -1:
            spans.append({'text': text[paren_start:], 'italic': True})
            break

        spans.append({'text': text[paren_start:paren_end + 1], 'italic': True})
        i = paren_end + 1

    return spans


def _discipline_ref_to_code(label):
    raw = (label or '').strip()
    if not raw:
        return None, False

    is_superior = raw.isupper() and raw.lower() != raw
    low = raw.lower()
    if low.startswith('superior '):
        is_superior = True
        raw = raw[9:].strip()
        low = raw.lower()

    aliases = {
        'abombwe': 'abo',
        'animalism': 'ani',
        'auspex': 'aus',
        'celerity': 'cel',
        'chimerstry': 'chi',
        'daimoinon': 'dai',
        'defense': 'def',
        'dementation': 'dem',
        'dominate': 'dom',
        'flight': 'flight',
        'fortitude': 'for',
        'innocence': 'inn',
        'judgment': 'jus',
        'maleficia': 'mal',
        'martyrdom': 'mar',
        'melpominee': 'mel',
        'mytherceria': 'myt',
        'necromancy': 'nec',
        'obeah': 'obe',
        'obfuscate': 'obf',
        'oblivion': 'obl',
        'obtenebration': 'obt',
        'potence': 'pot',
        'presence': 'pre',
        'protean': 'pro',
        'quietus': 'qui',
        'redemption': 'red',
        'sanguinus': 'san',
        'serpentis': 'ser',
        'spiritus': 'spi',
        'striga': 'str',
        'temporis': 'tem',
        'thanatosis': 'tha',
        'thaumaturgy': 'thn',
        'blood sorcery': 'thn',
        'valeren': 'val',
        'vengeance': 'ven',
        'vicissitude': 'vic',
        'vision': 'vin',
        'visceratika': 'vis',
    }

    direct_codes = set(aliases.values())
    code = low if low in direct_codes else aliases.get(low)
    return code, is_superior


def _discipline_symbol_path(code, is_superior):
    folder = 'disc_sup' if is_superior else 'disc_inf'
    base = os.path.join(settings.BASE_DIR, 'static', folder, code)
    png_path = base + '.png'
    if os.path.exists(png_path):
        return png_path
    svg_path = base + '.svg'
    if os.path.exists(svg_path):
        return svg_path
    return None


def _special_symbol_path(symbol):
    if symbol == 'Ⓓ':
        candidates = [
            os.path.join(settings.BASE_DIR, 'static', 'icons', 'directed.png'),
            os.path.join(settings.BASE_DIR, 'static', 'icons', 'directed.svg'),
            os.path.join(settings.BASE_DIR, 'static', 'icons', 'direcd.png'),
            os.path.join(settings.BASE_DIR, 'static', 'icons', 'direcd.svg'),
        ]
        for icon_path in candidates:
            if os.path.exists(icon_path):
                return icon_path
    return None


def _inline_symbol_path(symbol):
    raw = (symbol or '').strip()
    if raw.startswith('[') and raw.endswith(']'):
        code, is_superior = _discipline_ref_to_code(raw[1:-1])
        if code:
            return _discipline_symbol_path(code, is_superior)
        return None
    return _special_symbol_path(raw)


def _append_text_tokens_with_inline_symbols(tokens, text, font, style, font_size):
    parts = re.split(r'(\[[^\]]+\])', text or '')
    for part in parts:
        if not part:
            continue

        icon_path = _inline_symbol_path(part)
        if icon_path:
            tokens.append({
                'type': 'symbol',
                'path': icon_path,
                'size': max(20, int(font_size * 1.05)),
                'gap': max(4, int(font_size * 0.18)),
                'style': style,
                'font': font,
            })
            continue

        normalized = part.replace('Ⓓ', ' Ⓓ ')
        if style == 'italic':
            if normalized:
                tokens.append({
                    'type': 'text',
                    'text': normalized,
                    'font': font,
                    'style': 'italic',
                })
            continue

        words = normalized.split(' ')
        for wi, word in enumerate(words):
            if wi > 0:
                word = ' ' + word
            if not word:
                continue
            raw_word = word.strip()
            icon_path = _inline_symbol_path(raw_word)
            if icon_path:
                tokens.append({
                    'type': 'symbol',
                    'path': icon_path,
                    'size': max(20, int(font_size * 1.05)),
                    'gap': max(4, int(font_size * 0.18)),
                    'style': style,
                    'font': font,
                })
                continue
            tokens.append({
                'type': 'text',
                'text': word,
                'font': font,
                'style': style,
            })


def _segment_to_tokens_libreria(segments, font_size):
    font_bold, font_normal = _load_hab_fonts(font_size)
    tokens = []

    for seg in segments:
        style = seg['style']
        font = font_bold if style == 'bold' else font_normal
        parts = re.split(r'(\[[^\]]+\])', seg['text'])

        for part in parts:
            if not part:
                continue

            lines = part.split('\n')
            for li, line in enumerate(lines):
                if line:
                    spans = _split_parentheses_italic(line)
                    for span in spans:
                        _append_text_tokens_with_inline_symbols(
                            tokens,
                            span['text'],
                            font,
                            'italic' if span['italic'] else style,
                            font_size,
                        )
                if li < len(lines) - 1:
                    tokens.append({'type': 'newline'})

    return tokens


# --- Helper: renderiza texto con word-wrap y múltiples estilos ---
def _render_habilidad_text(image, text, x, y, max_width, font_size, color, bg_opacity=180,
                           bg_padding=10, bg_radius=12, line_spacing=3, bg_color=(0, 0, 0),
                           box_height=None):
    """Renderiza el texto de habilidad con formato mixto, word-wrap y fondo redondeado."""
    font_bold, font_normal = _load_hab_fonts(font_size)
    segments = _parse_habilidad(text)
    if not segments:
        return

    pad = int(bg_padding)
    outer_x = int(x)
    outer_y = int(y)
    outer_width = max(1, int(max_width))
    content_x = outer_x + pad
    content_y = outer_y + pad
    content_width = max(1, outer_width - (pad * 2))

    # --- Primer paso: calcular dimensiones del texto (dry run) ---
    words = []
    for seg in segments:
        style = seg['style']
        font = font_bold if style == 'bold' else font_normal
        _append_text_tokens_with_inline_symbols(words, seg['text'], font, style, font_size)

    line_height = font_size + line_spacing
    cur_x = content_x
    cur_y = content_y
    max_right = content_x
    for word_info in words:
        if word_info.get('type') == 'symbol':
            w_width = word_info['size'] + word_info['gap']
            w_text = None
            w_font = word_info['font']
        else:
            w_text = word_info['text']
            w_font = word_info['font']
            bbox = w_font.getbbox(w_text)
            w_width = bbox[2] - bbox[0]
        if cur_x + w_width > content_x + content_width and cur_x > content_x:
            cur_x = content_x
            cur_y += line_height
            if w_text and w_text.startswith(' '):
                w_text = w_text.lstrip(' ')
                bbox = w_font.getbbox(w_text)
                w_width = bbox[2] - bbox[0]
        if cur_x + w_width > max_right:
            max_right = cur_x + w_width
        cur_x += w_width

    text_bottom = cur_y + line_height

    # --- Dibujar recuadro redondeado con transparencia ---
    rx, ry = outer_x, outer_y
    rw = outer_width
    # Altura fija si se especifica box_height, dinámica si no
    if box_height is not None:
        rh = box_height
    else:
        rh = max(1, (text_bottom - content_y) + (pad * 2))
    bg_opacity = max(0, min(255, int(bg_opacity)))
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [rx, ry, rx + rw, ry + rh],
        radius=bg_radius,
        fill=(*bg_color, bg_opacity)
    )
    image.alpha_composite(overlay)

    # --- Segundo paso: construir líneas ---
    text_width = content_width
    lines = []
    current_line = []
    cur_x = content_x
    for word_info in words:
        w_font = word_info['font']
        w_style = word_info['style']
        if word_info.get('type') == 'symbol':
            w_text = None
            w_width = word_info['size'] + word_info['gap']
        else:
            w_text = word_info['text']
            bbox = w_font.getbbox(w_text)
            w_width = bbox[2] - bbox[0]
        if cur_x + w_width > content_x + text_width and cur_x > content_x:
            lines.append(current_line)
            current_line = []
            cur_x = content_x
            if w_text and w_text.startswith(' '):
                w_text = w_text.lstrip(' ')
                bbox = w_font.getbbox(w_text)
                w_width = bbox[2] - bbox[0]
        if word_info.get('type') == 'symbol':
            current_line.append({
                'type': 'symbol',
                'path': word_info['path'],
                'size': word_info['size'],
                'gap': word_info['gap'],
                'style': w_style,
                'font': w_font,
            })
        else:
            current_line.append({'type': 'text', 'text': w_text, 'style': w_style, 'font': w_font})
        cur_x += w_width
    if current_line:
        lines.append(current_line)

    # --- Tercer paso: dibujar líneas centradas (sin justificado a extremos) ---
    draw = ImageDraw.Draw(image)
    content_height = max(1, len(lines)) * line_height
    if box_height is not None:
        inner_top = outer_y + pad
        inner_height = max(1, rh - (pad * 2))
        cur_y = inner_top + max(0, (inner_height - content_height) // 2)
    else:
        cur_y = content_y
    symbol_cache = {}
    icon_vertical_nudge = max(2, int(font_size * 0.16))
    for line in lines:
        # Calcular ancho de cada token
        stripped_words = []
        word_widths = []
        token_is_symbol = []
        for winfo in line:
            if winfo.get('type') == 'symbol':
                stripped_words.append('')
                word_widths.append(winfo['size'] + winfo['gap'])
                token_is_symbol.append(True)
            else:
                stripped = winfo['text'].lstrip(' ')
                stripped_words.append(stripped)
                bbox = winfo['font'].getbbox(stripped)
                word_widths.append(bbox[2] - bbox[0])
                token_is_symbol.append(False)

        line_width = sum(word_widths)
        num_words = len(line)
        if num_words > 1:
            for i, winfo in enumerate(line[:-1]):
                if not token_is_symbol[i]:
                    sp = winfo['font'].getbbox(' ')
                    line_width += sp[2] - sp[0]
                else:
                    line_width += max(2, int(font_size * 0.1))

        cur_x = content_x + max(0, (text_width - line_width) // 2)
        for i, winfo in enumerate(line):
            if token_is_symbol[i]:
                cache_key = (winfo['path'], winfo['size'])
                icon = symbol_cache.get(cache_key)
                if icon is None:
                    icon = _load_symbol(winfo['path'], winfo['size'])
                    symbol_cache[cache_key] = icon
                image.alpha_composite(icon, (int(cur_x), int(cur_y + max(0, (line_height - winfo['size']) // 2) - icon_vertical_nudge)))
            else:
                t = stripped_words[i]
                if winfo['style'] == 'italic':
                    _draw_italic(image, int(cur_x), cur_y, t, winfo['font'], color, font_size)
                else:
                    draw.text((int(cur_x), cur_y), t, font=winfo['font'], fill=color)
            cur_x += word_widths[i]
            if i < num_words - 1:
                if not token_is_symbol[i]:
                    sp = winfo['font'].getbbox(' ')
                    cur_x += sp[2] - sp[0]
                else:
                    cur_x += max(2, int(font_size * 0.1))
        cur_y += line_height


def _draw_italic(image, x, y, text, font, color, font_size):
    """Simula texto en cursiva usando transformación de cizalla (shear)."""
    if not text:
        return

    leading_spaces = len(text) - len(text.lstrip(' '))
    if leading_spaces > 0:
        space_bbox = font.getbbox(' ')
        x += (space_bbox[2] - space_bbox[0]) * leading_spaces
        text = text.lstrip(' ')
        if not text:
            return

    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0] + 10
    h = bbox[3] - bbox[1] + 10
    shear = 0.2
    extra_w = int(h * shear) + 5
    tmp = Image.new('RGBA', (w + extra_w, h), (0, 0, 0, 0))
    tmp_draw = ImageDraw.Draw(tmp)
    tmp_draw.text((extra_w // 2, -bbox[1]), text, font=font, fill=color)
    # Aplicar transformación affine para cizalla
    tmp = tmp.transform(
        tmp.size, Image.AFFINE,
        (1, shear, -shear * h / 2, 0, 1, 0),
        resample=Image.BICUBIC
    )
    image.alpha_composite(tmp, (x, y))


def _render_habilidad_text_libreria(image, text, x, y, max_width, font_size, color, bg_opacity=180,
                                    bg_padding=10, bg_radius=12, line_spacing=3, bg_color=(0, 0, 0),
                                    box_height=None):
    segments = _parse_libreria_habilidad(text)
    if not segments:
        return

    pad = int(bg_padding)
    outer_x = int(x)
    outer_y = int(y)
    outer_width = max(1, int(max_width))
    content_x = outer_x + pad
    content_y = outer_y + pad
    content_width = max(1, outer_width - (pad * 2))

    tokens = _segment_to_tokens_libreria(segments, font_size)
    if not tokens:
        return

    line_height = int(font_size * 1.15) + line_spacing
    text_width_limit = content_width

    lines = []
    current_line = []
    current_width = 0

    for tok in tokens:
        if tok['type'] == 'newline':
            lines.append(current_line)
            current_line = []
            current_width = 0
            continue

        if tok['type'] == 'text':
            bbox = tok['font'].getbbox(tok['text'])
            tok_w = bbox[2] - bbox[0]
            if tok.get('style') == 'italic':
                tok_w += max(2, int(font_size * 0.08))
        else:
            tok_w = tok['size'] + tok['gap']

        if current_width + tok_w > text_width_limit and current_line:
            lines.append(current_line)
            current_line = []
            current_width = 0
            if tok['type'] == 'text':
                tok = dict(tok)
                tok['text'] = tok['text'].lstrip(' ')
                bbox = tok['font'].getbbox(tok['text'])
                tok_w = bbox[2] - bbox[0]

        current_line.append(tok)
        current_width += tok_w

    if current_line:
        lines.append(current_line)

    pad = bg_padding
    rx, ry = outer_x, outer_y
    rw = outer_width
    if box_height is not None:
        rh = box_height
    else:
        rh = max(line_height + (pad * 2), len(lines) * line_height + (pad * 2))

    bg_opacity = max(0, min(255, int(bg_opacity)))
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle(
        [rx, ry, rx + rw, ry + rh],
        radius=bg_radius,
        fill=(*bg_color, bg_opacity)
    )
    image.alpha_composite(overlay)

    draw = ImageDraw.Draw(image)
    content_height = max(1, len(lines)) * line_height
    if box_height is not None:
        inner_top = outer_y + pad
        inner_height = max(1, rh - (pad * 2))
        cy = inner_top + max(0, (inner_height - content_height) // 2)
    else:
        cy = content_y
    symbol_cache = {}
    icon_vertical_nudge = max(2, int(font_size * 0.16))
    for line in lines:
        line_width = 0
        for tok in line:
            if tok['type'] == 'text':
                bbox = tok['font'].getbbox(tok['text'])
                tok_w = bbox[2] - bbox[0]
                if tok.get('style') == 'italic':
                    tok_w += max(2, int(font_size * 0.08))
            else:
                tok_w = tok['size'] + tok['gap']
            line_width += tok_w

        cx = content_x + max(0, (text_width_limit - line_width) // 2)
        for tok in line:
            if tok['type'] == 'text':
                if tok.get('style') == 'italic':
                    _draw_italic(image, int(cx), cy, tok['text'], tok['font'], color, font_size)
                else:
                    draw.text((int(cx), cy), tok['text'], font=tok['font'], fill=color)
                bbox = tok['font'].getbbox(tok['text'])
                cx += bbox[2] - bbox[0]
                if tok.get('style') == 'italic':
                    cx += max(2, int(font_size * 0.08))
            else:
                cache_key = (tok['path'], tok['size'])
                icon = symbol_cache.get(cache_key)
                if icon is None:
                    icon = _load_symbol(tok['path'], tok['size'])
                    symbol_cache[cache_key] = icon
                image.alpha_composite(icon, (int(cx), int(cy + max(0, (line_height - tok['size']) // 2) - icon_vertical_nudge)))
                cx += tok['size'] + tok['gap']
        cy += line_height


# --- Helper principal: renderiza TODOS los elementos sobre la imagen base ---
def _render_carta(imagen_url, nombre='', clan='', senda='', disciplinas=None, simbolos=None, habilidad='', coste='', cripta='', ilustrador='', hab_opacity=180, hab_font_size=None, card_type='cripta', layout_name=None, layout_config=None, dynamic_habilidad_from_bottom=False):
    """
    Renderiza todos los elementos de la carta sobre la imagen base.
    Cada elemento tiene posición fija e independiente:
    - Nombre: posición de layouts/<ACTIVE_LAYOUT>.py (no depende de símbolos)
    - Clan: posición fija CLAN_X, CLAN_Y (no depende del nombre)
    - Senda: posición fija SENDA_X, SENDA_Y (no depende del nombre)
    - Disciplinas: columna vertical empezando en DISC_X, DISC_START_Y
    - Habilidad: cuadro de texto con formato mixto
    """
    imagen_abspath = _resolve_imagen_path(imagen_url)
    if not os.path.exists(imagen_abspath):
        return None, 'Imagen no encontrada'

    lay = layout_config if layout_config is not None else _load_layout(layout_name)
    lc  = lay['carta']
    card_type = _normalize_card_type(card_type)

    layout_scope = lay.get('libreria', {}) if card_type == 'libreria' else lay
    ln  = layout_scope.get('nombre') or lay.get('nombre')
    lcl = layout_scope.get('clan') or lay.get('clan')
    ls  = layout_scope.get('senda') or lay.get('senda')
    ld  = layout_scope.get('disciplinas') or lay.get('disciplinas')
    lsi = (layout_scope.get('simbolos') or lay.get('simbolos')) if card_type == 'libreria' else None
    lh  = layout_scope.get('habilidad') or lay.get('habilidad')
    lco = layout_scope.get('coste') or lay.get('coste')
    lcr = lay.get('cripta') if card_type == 'cripta' else None
    lil = layout_scope.get('ilustrador') or lay.get('ilustrador')
    metrics = _compute_layout_metrics(
        lay,
        card_type=card_type,
        habilidad=habilidad,
        nombre=nombre,
        ilustrador=ilustrador,
        disciplinas=disciplinas,
        simbolos=simbolos,
        dynamic_habilidad_from_bottom=dynamic_habilidad_from_bottom,
        hab_font_size=hab_font_size,
    )

    card_w = lc['width']
    card_h = lc['height']

    image = Image.open(imagen_abspath).convert('RGBA')
    image = image.resize((card_w, card_h), Image.LANCZOS)

    # --- Variables locales desde el layout activo ---
    clan_size    = lcl['size']
    clan_x       = lcl['x']
    clan_y       = lcl['y']

    if ls:
        senda_size = ls['size']
        senda_x = ls['x']
        senda_y = ls['y']

    simbolos_metrics = metrics.get('simbolos') or {}
    simbolos_box = simbolos_metrics.get('box') or {}
    simbolos_size = int(simbolos_metrics.get('size', lsi.get('size', 64) if lsi else 64))
    simbolos_x = int(simbolos_box.get('x', lsi.get('x', 0) if lsi else 0))
    simbolos_y = int(simbolos_box.get('y', lsi.get('y', 0) if lsi else 0))
    simbolos_spacing = int(simbolos_metrics.get('spacing', lsi.get('spacing', 80) if lsi else 80))
    simbolos_box_bottom = simbolos_y + int(simbolos_box.get('height', simbolos_size * max(1, len(simbolos or []))))

    disc_metrics = metrics.get('disciplinas') or {}
    disc_box = disc_metrics.get('box') or {}
    disc_size = int(disc_metrics.get('size', ld['size']))
    disc_spacing = int(disc_metrics.get('spacing', ld['spacing']))
    disc_x = int(disc_box.get('x', ld['x']))
    disc_source = disc_metrics.get('source', 'legacy')

    default_hab_font_size = int(lh['font_size'])
    if hab_font_size is None:
        hab_font_size = default_hab_font_size
    else:
        hab_font_size = max(20, min(int(hab_font_size), 80))
    hab_metrics = metrics.get('habilidad') or {}
    hab_box = hab_metrics.get('used_box') or hab_metrics.get('box') or {}
    hab_x         = int(hab_box.get('x', lh['x']))
    hab_y         = int(hab_box.get('y', int(card_h * lh['y_ratio'])))
    hab_max_w     = int(hab_box.get('width', int(card_w * lh['max_width_ratio'])))
    hab_padding   = lh['bg_padding']
    hab_radius    = lh['bg_radius']
    hab_line_sp   = lh['line_spacing']
    hab_box_h     = int(hab_box.get('height')) if hab_box else (int(card_h * lh['box_bottom_ratio']) - hab_y if 'box_bottom_ratio' in lh else None)

    coste_size   = lco['size']
    coste_bottom = lco['bottom']
    coste_right  = lco.get('right')
    coste_left   = lco.get('left')

    if lcr:
        cripta_font_size = lcr['font_size']
        cripta_y_gap = lcr['y_gap']

    if lil:
        il_font_size = lil['font_size']
        il_bottom = lil['bottom']

    # 1) Nombre (independiente de los símbolos)
    if nombre:
        nombre_metrics = metrics.get('nombre', {})
        fitted = nombre_metrics.get('fit') or {}
        rendered_name = fitted.get('text', nombre)
        font = fitted.get('font')
        if font is None:
            font_path = os.path.join(settings.BASE_DIR, ln['font_path'])
            if not os.path.exists(font_path):
                raise FileNotFoundError(f"No se encontró la fuente en {font_path}")
            font = ImageFont.truetype(font_path, ln['font_size'])
        text_width = fitted.get('width')
        if text_width is None:
            text_width = _measure_text_width(font, rendered_name)

        nombre_box = nombre_metrics.get('box') or ln.get('box') or {'x': ln.get('x', 0), 'y': ln.get('y', 0), 'width': card_w, 'height': ln.get('font_size', 40)}
        align = nombre_metrics.get('align', 'left')
        draw = ImageDraw.Draw(image)
        x = _compute_aligned_x(nombre_box['x'], text_width, align, nombre_box['width'])
        y = int(nombre_box['y']) + max(0, (int(nombre_box['height']) - int(fitted.get('font_size', ln.get('font_size', 40)))) // 2)

        shadow = ln.get('shadow', {})
        if nombre_metrics.get('shadow_enabled', shadow.get('enabled', False)):
            for dx, dy in shadow.get('offsets', []):
                draw.text((x + dx, y + dy), rendered_name, font=font, fill=shadow.get('color', 'black'))
        draw.text((x, y), rendered_name, font=font, fill=ln.get('color', 'white'))

    # 2) Símbolo de clan (posición fija, independiente del nombre)
    if clan:
        clan_symbol_path = os.path.join(settings.BASE_DIR, 'static/clan_symbols', clan)
        if os.path.exists(clan_symbol_path):
            try:
                clan_img = _load_symbol(clan_symbol_path, clan_size)
                image.alpha_composite(clan_img, (clan_x, clan_y))
            except Exception as e:
                print(f'Error renderizando símbolo de clan: {e}')
        else:
            print(f"[DEBUG] Archivo de clan no encontrado: {clan_symbol_path}")

    # 3) Símbolo de senda/path (posición fija, independiente del nombre)
    if senda and ls:
        senda_symbol_path = os.path.join(settings.BASE_DIR, 'static/path', senda)
        if os.path.exists(senda_symbol_path):
            try:
                senda_img = _load_symbol(senda_symbol_path, senda_size)
                image.alpha_composite(senda_img, (senda_x, senda_y))
            except Exception as e:
                print(f'Error renderizando símbolo de senda: {e}')
        else:
            print(f"[DEBUG] Archivo de senda no encontrado: {senda_symbol_path}")

    # 4) Símbolos de librería (columna vertical de arriba a abajo)
    if card_type == 'libreria' and simbolos and lsi:
        y_top = simbolos_y
        for sym in simbolos:
            sym_name = os.path.basename(str(sym)).strip()
            if not sym_name:
                continue
            if sym_name.lower().endswith('.png') or sym_name.lower().endswith('.svg'):
                sym_base = sym_name.rsplit('.', 1)[0]
            else:
                sym_base = sym_name

            sym_path = os.path.join(settings.BASE_DIR, 'static/icons', sym_base + '.png')
            if not os.path.exists(sym_path):
                sym_path = os.path.join(settings.BASE_DIR, 'static/icons', sym_base + '.svg')

            if os.path.exists(sym_path):
                try:
                    if y_top + simbolos_size > simbolos_box_bottom:
                        break
                    sym_img = _load_symbol(sym_path, simbolos_size)
                    image.alpha_composite(sym_img, (simbolos_x, y_top))
                    y_top += simbolos_spacing
                except Exception as e:
                    print(f'Error renderizando símbolo de librería {sym_base}: {e}')
            else:
                print(f"[DEBUG] Archivo de símbolo de librería no encontrado: {sym_base}")

    # 5) Disciplinas (columna vertical: disc_sup abajo, disc_inf encima)
    if disciplinas:
        disc_sup_images = []
        disc_inf_images = []
        for disc in disciplinas:
            disc_name = disc.get('name', '')
            disc_level = disc.get('level', 'inf')
            if not disc_name:
                continue
            if disc_level == 'sup':
                disc_folder = os.path.join(settings.BASE_DIR, 'static/disc_sup')
            else:
                disc_folder = os.path.join(settings.BASE_DIR, 'static/disc_inf')
            disc_path = os.path.join(disc_folder, disc_name + '.png')
            if not os.path.exists(disc_path):
                disc_path = os.path.join(disc_folder, disc_name + '.svg')
            if os.path.exists(disc_path):
                try:
                    img = _load_symbol(disc_path, disc_size)
                    if disc_level == 'sup':
                        disc_sup_images.append(img)
                    else:
                        disc_inf_images.append(img)
                except Exception as e:
                    print(f'Error renderizando disciplina {disc_name}: {e}')
            else:
                print(f"[DEBUG] Archivo de disciplina no encontrado: {disc_path}")
        # sup en los slots inferiores (Z abajo, A arriba), inf encima (Z abajo, A arriba)
        # Se invierten porque pintamos de abajo a arriba: la última pintada queda más alta
        all_discs = list(reversed(disc_sup_images)) + list(reversed(disc_inf_images))
        if all_discs:
            disc_positions = _compute_vertical_stack_positions(
                box=disc_box,
                item_size=disc_size,
                spacing=disc_spacing,
                item_count=len(all_discs),
                source=disc_source,
            )
            disc_images = all_discs
            for disc_img, disc_y in zip(disc_images, disc_positions):
                image.alpha_composite(disc_img, (disc_x, disc_y))

    # Base Y del recuadro de habilidad (se computa siempre)
    pad = hab_padding

    # 6) Número de cripta (sobre el recuadro, pegado a la izquierda)
    if card_type == 'cripta' and cripta and lcr:
        try:
            cripta_metrics = metrics.get('cripta') or {}
            cripta_style = cripta_metrics.get('style') or {}
            effective_cripta_font_size = int(cripta_style.get('font_size', cripta_font_size))
            effective_cripta_color = cripta_style.get('color', lcr['color'])
            font_bold, _ = _load_hab_fonts(effective_cripta_font_size)
            cripta_box = cripta_metrics.get('box') or {
                'x': hab_x - pad,
                'y': hab_y - (pad * 2) - effective_cripta_font_size - cripta_y_gap,
                'width': max(30, effective_cripta_font_size * 2),
                'height': max(30, effective_cripta_font_size + 8),
            }
            cripta_x = int(cripta_box['x'])
            cripta_y = int(cripta_box['y']) + max(0, (int(cripta_box['height']) - effective_cripta_font_size) // 2)
            draw_cripta = ImageDraw.Draw(image)
            draw_cripta.text((cripta_x, cripta_y), str(cripta), font=font_bold, fill=effective_cripta_color)
        except Exception as e:
            print(f'Error renderizando cripta: {e}')

    # 7) Habilidad (cuadro de texto con formato mixto)
    if habilidad:
        try:
            _render_habilidad_text(
                image, habilidad, hab_x, hab_y, hab_max_w, hab_font_size, lh['color'],
                bg_opacity=hab_opacity, bg_padding=hab_padding,
                bg_radius=hab_radius, line_spacing=hab_line_sp,
                bg_color=tuple(lh['bg_color']), box_height=hab_box_h
            )
        except Exception as e:
            print(f'Error renderizando habilidad: {e}')

    # 8) Ilustrador (centrado, pegado a la parte inferior de la carta)
    if ilustrador and lil:
        try:
            ilustrador_metrics = metrics.get('ilustrador', {})
            il_style = ilustrador_metrics.get('style') or {}
            effective_il_font_size = int(il_style.get('font_size', il_font_size))
            effective_il_color = il_style.get('color', lil['color'])
            il_fit = ilustrador_metrics.get('fit') or {}
            rendered_il = il_fit.get('text', ilustrador)
            font_normal = il_fit.get('font')
            if font_normal is None:
                _, font_normal = _load_hab_fonts(effective_il_font_size)
            il_w = il_fit.get('width')
            if il_w is None:
                il_bbox = font_normal.getbbox(rendered_il)
                il_w = il_bbox[2] - il_bbox[0]

            il_box = ilustrador_metrics.get('box') or lil.get('box') or {
                'x': 45,
                'y': image.height - il_bottom - il_font_size,
                'width': max(1, image.width - 90),
                'height': il_font_size + 8,
            }
            il_align = ilustrador_metrics.get('align', 'left')
            il_x = _compute_aligned_x(il_box['x'], il_w, il_align, il_box['width'])
            il_y = int(il_box['y']) + max(0, (int(il_box['height']) - int(il_fit.get('font_size', effective_il_font_size))) // 2)
            draw_il = ImageDraw.Draw(image)
            draw_il.text((il_x, il_y), rendered_il, font=font_normal, fill=effective_il_color)
        except Exception as e:
            print(f'Error renderizando ilustrador: {e}')

    # 9) Coste (símbolo abajo a la derecha)
    print(f'[DEBUG] coste recibido: "{coste}" (type={type(coste).__name__})')
    if coste:
        coste_path = None
        if card_type == 'libreria':
            raw_coste = str(coste).strip().lower()
            candidates = []
            if raw_coste.isdigit():
                candidates.append(f'pool{raw_coste}.png')
            elif raw_coste in ('x', 'poolx'):
                candidates.append('poolx.png')
            elif raw_coste in ('bloodx',):
                candidates.append('bloodx.png')
            else:
                candidates.append(f'{raw_coste}.png')

            for file_name in candidates:
                probe = os.path.join(settings.BASE_DIR, 'static/costes_lib', file_name)
                if os.path.exists(probe):
                    coste_path = probe
                    break
        else:
            coste_file = f'cap{coste}.gif'
            probe = os.path.join(settings.BASE_DIR, 'static/costes', coste_file)
            if os.path.exists(probe):
                coste_path = probe

        print(f'[DEBUG] coste_path: {coste_path}, exists: {os.path.exists(coste_path)}')
        if coste_path and os.path.exists(coste_path):
            try:
                coste_img = Image.open(coste_path).convert('RGBA')
                coste_img = coste_img.resize((coste_size, coste_size), Image.LANCZOS)
                if coste_left is not None:
                    coste_x = int(coste_left)
                elif coste_right is not None:
                    coste_x = image.width - int(coste_right) - coste_size
                else:
                    coste_x = image.width - 40 - coste_size
                coste_y = image.height - coste_bottom - coste_size
                image.alpha_composite(coste_img, (coste_x, coste_y))
            except Exception as e:
                print(f'Error renderizando coste: {e}')
        else:
            print(f'[DEBUG] Archivo de coste no encontrado para valor: {coste}')

    # Guardar imagen renderizada
    render_dir = os.path.join(settings.MEDIA_ROOT, 'render')
    os.makedirs(render_dir, exist_ok=True)
    filename = f'render_{get_random_string(8)}.png'
    render_path = os.path.join(render_dir, filename)
    image.save(render_path, 'PNG')
    render_url = settings.MEDIA_URL + 'render/' + filename
    return render_url, None


def _render_carta_from_path(imagen_abspath, **kwargs):
    imagen_url = _prepare_render_source_from_path(
        imagen_abspath,
        target_name=kwargs.get('nombre') or os.path.basename(imagen_abspath),
    )
    if not imagen_url:
        return None, 'Imagen no encontrada'
    return _render_carta(imagen_url=imagen_url, **kwargs)


# --- Endpoints ---

@csrf_exempt
def render_nombre(request):
    """Se llama cuando cambia el nombre. Renderiza todo."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        nombre = (data.get('nombre') or '').strip()
        clan = (data.get('clan') or '').strip()
        senda = (data.get('senda') or '').strip()
        disciplinas = data.get('disciplinas') or []
        simbolos = data.get('simbolos') or []
        habilidad = (data.get('habilidad') or '').strip()
        coste = (data.get('coste') or '').strip()
        cripta = str(data.get('cripta') or '').strip()
        ilustrador = (data.get('ilustrador') or '').strip()
        hab_opacity = int(data.get('hab_opacity', 180))
        hab_font_size = int(data.get('hab_font_size', 33))
        dynamic_habilidad_from_bottom = _coerce_bool(data.get('dynamic_habilidad_from_bottom', False))
        card_type = _normalize_card_type(data.get('card_type'))
        layout_name = (data.get('layout_name') or '').strip()
        layout_id = data.get('layout_id')
        layout_override = data.get('layout_override')
        imagen_url = data.get('imagen_url', '')
        if not imagen_url:
            return JsonResponse({'error': 'Faltan datos'}, status=400)

        resolved_layout = _resolve_layout_config(
            request_user=request.user,
            card_type=card_type,
            layout_id=layout_id,
            layout_name=layout_name,
            layout_override=layout_override,
        )

        render_url, error = _render_carta(
            imagen_url,
            nombre=nombre,
            clan=clan,
            senda=senda,
            disciplinas=disciplinas,
            simbolos=simbolos,
            habilidad=habilidad,
            coste=coste,
            cripta=cripta,
            ilustrador=ilustrador,
            hab_opacity=hab_opacity,
            hab_font_size=hab_font_size,
            card_type=card_type,
            layout_name=layout_name,
            layout_config=resolved_layout,
            dynamic_habilidad_from_bottom=dynamic_habilidad_from_bottom,
        )
        if error:
            return JsonResponse({'error': error}, status=404)
        return JsonResponse({'imagen_url': render_url})
    except LayoutOwnershipError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except LayoutValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        import traceback
        print('ERROR EN SERVICIO DE TEXTO (nombre):')
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'trace': traceback.format_exc()}, status=500)


@csrf_exempt
def render_clan(request):
    """Se llama cuando cambia el clan o la senda. Renderiza todo."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        clan = (data.get('clan') or '').strip()
        nombre = (data.get('nombre') or '').strip()
        senda = (data.get('senda') or '').strip()
        disciplinas = data.get('disciplinas') or []
        simbolos = data.get('simbolos') or []
        habilidad = (data.get('habilidad') or '').strip()
        coste = (data.get('coste') or '').strip()
        cripta = str(data.get('cripta') or '').strip()
        ilustrador = (data.get('ilustrador') or '').strip()
        hab_opacity = int(data.get('hab_opacity', 180))
        hab_font_size = int(data.get('hab_font_size', 33))
        dynamic_habilidad_from_bottom = _coerce_bool(data.get('dynamic_habilidad_from_bottom', False))
        card_type = _normalize_card_type(data.get('card_type'))
        layout_name = (data.get('layout_name') or '').strip()
        layout_id = data.get('layout_id')
        layout_override = data.get('layout_override')
        imagen_url = data.get('imagen_url', '')
        if not imagen_url:
            return JsonResponse({'error': 'Faltan datos'}, status=400)

        resolved_layout = _resolve_layout_config(
            request_user=request.user,
            card_type=card_type,
            layout_id=layout_id,
            layout_name=layout_name,
            layout_override=layout_override,
        )

        render_url, error = _render_carta(
            imagen_url,
            nombre=nombre,
            clan=clan,
            senda=senda,
            disciplinas=disciplinas,
            simbolos=simbolos,
            habilidad=habilidad,
            coste=coste,
            cripta=cripta,
            ilustrador=ilustrador,
            hab_opacity=hab_opacity,
            hab_font_size=hab_font_size,
            card_type=card_type,
            layout_name=layout_name,
            layout_config=resolved_layout,
            dynamic_habilidad_from_bottom=dynamic_habilidad_from_bottom,
        )
        if error:
            return JsonResponse({'error': error}, status=404)
        return JsonResponse({'imagen_url': render_url})
    except LayoutOwnershipError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except LayoutValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        import traceback
        print('ERROR EN SERVICIO DE TEXTO (clan):')
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'trace': traceback.format_exc()}, status=500)


@csrf_exempt
def render_texto(request):
    """Endpoint legacy. Renderiza todo."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        nombre = (data.get('nombre') or '').strip()
        clan = (data.get('clan') or '').strip()
        senda = (data.get('senda') or '').strip()
        disciplinas = data.get('disciplinas') or []
        simbolos = data.get('simbolos') or []
        habilidad = (data.get('habilidad') or '').strip()
        coste = (data.get('coste') or '').strip()
        cripta = str(data.get('cripta') or '').strip()
        ilustrador = (data.get('ilustrador') or '').strip()
        hab_opacity = int(data.get('hab_opacity', 180))
        hab_font_size = int(data.get('hab_font_size', 33))
        dynamic_habilidad_from_bottom = _coerce_bool(data.get('dynamic_habilidad_from_bottom', False))
        card_type = _normalize_card_type(data.get('card_type'))
        layout_name = (data.get('layout_name') or '').strip()
        layout_id = data.get('layout_id')
        layout_override = data.get('layout_override')
        imagen_url = data.get('imagen_url', '')
        if not imagen_url:
            return JsonResponse({'error': 'Faltan datos'}, status=400)

        resolved_layout = _resolve_layout_config(
            request_user=request.user,
            card_type=card_type,
            layout_id=layout_id,
            layout_name=layout_name,
            layout_override=layout_override,
        )

        render_url, error = _render_carta(
            imagen_url,
            nombre=nombre,
            clan=clan,
            senda=senda,
            disciplinas=disciplinas,
            simbolos=simbolos,
            habilidad=habilidad,
            coste=coste,
            cripta=cripta,
            ilustrador=ilustrador,
            hab_opacity=hab_opacity,
            hab_font_size=hab_font_size,
            card_type=card_type,
            layout_name=layout_name,
            layout_config=resolved_layout,
            dynamic_habilidad_from_bottom=dynamic_habilidad_from_bottom,
        )
        if error:
            return JsonResponse({'error': error}, status=404)
        return JsonResponse({'imagen_url': render_url})
    except LayoutOwnershipError as e:
        return JsonResponse({'error': str(e)}, status=403)
    except LayoutValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        import traceback
        print('ERROR EN SERVICIO DE TEXTO:')
        traceback.print_exc()
        return JsonResponse({'error': str(e), 'trace': traceback.format_exc()}, status=500)


@csrf_exempt
def guardar_carta(request):
    """Guarda la carta renderizada en la carpeta personal del usuario."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'No autenticado'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    try:
        data = json.loads(request.body.decode('utf-8'))
        render_url = (data.get('render_url') or '').strip()
        nombre_carta = (data.get('nombre') or '').strip().lower()
        if not render_url:
            return JsonResponse({'error': 'Falta render_url'}, status=400)

        filename_base = _safe_card_filename_base(nombre_carta)
        if not filename_base:
            return JsonResponse({'error': 'Falta nombre de carta'}, status=400)

        # Resolver ruta absoluta del render temporal
        # render_url puede venir como URL absoluta (http://...) o relativa (/media/...)
        from urllib.parse import urlparse
        path = urlparse(render_url).path  # extrae solo el path: /media/render/xxx.png
        if path.startswith(settings.MEDIA_URL):
            rel_path = path[len(settings.MEDIA_URL):]
        else:
            rel_path = path.lstrip('/')
        src_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        if not os.path.exists(src_path):
            return JsonResponse({'error': 'Archivo no encontrado'}, status=404)

        # Carpeta destino: media/cartas/<username>/
        username = request.user.username
        dest_dir = os.path.join(settings.MEDIA_ROOT, 'cartas', username)
        os.makedirs(dest_dir, exist_ok=True)

        filename = f'{filename_base}.png'
        counter = 2
        while os.path.exists(os.path.join(dest_dir, filename)):
            filename = f'{filename_base}_{counter}.png'
            counter += 1
        dest_path = os.path.join(dest_dir, filename)
        shutil.copy2(src_path, dest_path)

        # Limpiar carpetas temporales de media
        for tmp_folder in ('imagenes', 'recortes', 'render'):
            tmp_dir = os.path.join(settings.MEDIA_ROOT, tmp_folder)
            if os.path.isdir(tmp_dir):
                for fname in os.listdir(tmp_dir):
                    fpath = os.path.join(tmp_dir, fname)
                    try:
                        if os.path.isfile(fpath):
                            os.remove(fpath)
                    except Exception:
                        pass

        saved_url = settings.MEDIA_URL + f'cartas/{username}/{filename}'
        return JsonResponse({'ok': True, 'url': saved_url})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def buscar_cartas(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    card_type = (request.GET.get('card_type') or 'cripta').strip().lower()
    query = (request.GET.get('q') or '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    try:
        limit = int(request.GET.get('limit') or 10)
    except (TypeError, ValueError):
        limit = 10

    results = search_card_suggestions(card_type, query, limit=limit)
    return JsonResponse({'results': results})


def autocompletar_carta(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    card_type = (request.GET.get('card_type') or 'cripta').strip().lower()
    name = (request.GET.get('name') or '').strip()
    if not name:
        return JsonResponse({'error': 'Falta name'}, status=400)

    card = get_card_autocomplete(card_type, name)
    if not card:
        return JsonResponse({'error': 'Carta no encontrada'}, status=404)
    return JsonResponse({'card': card})
