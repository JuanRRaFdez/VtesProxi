import json
from copy import deepcopy
from pathlib import Path

from apps.layouts.models import UserLayout


CLASSIC_LAYOUTS_PATH = Path(__file__).resolve().parent.parent / 'srv_textos' / 'layouts.json'


def load_classic_seed(card_type):
    with CLASSIC_LAYOUTS_PATH.open(encoding='utf-8') as layouts_file:
        data = json.load(layouts_file)

    classic = data.get('layouts', {}).get('classic', {})
    normalized_card_type = (card_type or '').strip().lower()
    if normalized_card_type not in ('cripta', 'libreria'):
        normalized_card_type = 'cripta'

    if normalized_card_type == 'libreria':
        libreria = deepcopy(classic.get('libreria', {}))
        carta = classic.get('carta')
        if carta:
            libreria['carta'] = deepcopy(carta)
        return libreria

    return {
        key: deepcopy(value)
        for key, value in classic.items()
        if key != 'libreria' and not key.startswith('_')
    }


class LayoutValidationError(ValueError):
    pass


class LayoutOwnershipError(PermissionError):
    pass


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _expect_dict(payload, field_name):
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise LayoutValidationError(f'{field_name} debe ser un objeto')
    return value


def _expect_number(payload, field_name, min_value, max_value):
    value = payload.get(field_name)
    if not _is_number(value):
        raise LayoutValidationError(f'{field_name} debe ser numérico')
    if value < min_value or value > max_value:
        raise LayoutValidationError(f'{field_name} fuera de rango')


def _expect_ratio(payload, field_name):
    _expect_number(payload, field_name, 0, 1)


def _validate_habilidad_box(habilidad):
    bg_color = habilidad.get('bg_color')
    if bg_color is not None:
        if not isinstance(bg_color, list) or len(bg_color) != 3:
            raise LayoutValidationError('habilidad.bg_color debe tener 3 componentes')
        for value in bg_color:
            if not _is_number(value) or value < 0 or value > 255:
                raise LayoutValidationError('habilidad.bg_color fuera de rango')


_TEXT_RULE_DEFAULTS = {
    'nombre': {
        'align': 'center',
        'anchor_mode': 'free',
        'autoshrink': True,
        'ellipsis_enabled': True,
        'min_font_size': 18,
    },
    'ilustrador': {
        'align': 'left',
        'anchor_mode': 'free',
        'autoshrink': True,
        'ellipsis_enabled': True,
        'min_font_size': 14,
    },
}


def _coerce_legacy_y(raw_y, card_height):
    if isinstance(raw_y, bool):
        return 0
    if isinstance(raw_y, (int, float)):
        if isinstance(raw_y, float) and 0 <= raw_y <= 1:
            return int(card_height * raw_y)
        return int(raw_y)
    return 0


def _legacy_text_box(section_name, section, card_width, card_height):
    x = int(section.get('x', 0) or 0)
    font_size = int(section.get('font_size', 24) or 24)

    if section_name == 'ilustrador':
        bottom = int(section.get('bottom', 0) or 0)
        y = max(0, card_height - bottom - int(font_size * 1.2))
    else:
        y = _coerce_legacy_y(section.get('y', 0), card_height)

    width = max(40, int(card_width - max(0, x * 2)))
    height = max(font_size + 8, int(font_size * 1.6))
    return {
        'x': x,
        'y': y,
        'width': width,
        'height': height,
    }


def _ensure_text_v2_section(normalized, section_name):
    section = normalized.get(section_name)
    if not isinstance(section, dict):
        return

    carta = normalized.get('carta') or {}
    card_width = int(carta.get('width', 745) or 745)
    card_height = int(carta.get('height', 1040) or 1040)

    box = section.get('box')
    if not isinstance(box, dict):
        section['box'] = _legacy_text_box(section_name, section, card_width, card_height)
    else:
        section['box'] = deepcopy(box)
        section['box'].setdefault('x', 0)
        section['box'].setdefault('y', 0)
        section['box'].setdefault('width', card_width)
        section['box'].setdefault('height', 40)

    rules = section.get('rules')
    if not isinstance(rules, dict):
        rules = {}
        section['rules'] = rules

    for key, default_value in _TEXT_RULE_DEFAULTS.get(section_name, {}).items():
        rules.setdefault(key, default_value)


def _normalize_square_box(section, default_box):
    raw_box = section.get('box')
    if not isinstance(raw_box, dict):
        raw_box = default_box

    box = {
        'x': int(raw_box.get('x', default_box['x'])),
        'y': int(raw_box.get('y', default_box['y'])),
        'width': int(raw_box.get('width', default_box['width'])),
        'height': int(raw_box.get('height', default_box['height'])),
    }
    side = max(1, int(max(box['width'], box['height'])))
    box['width'] = side
    box['height'] = side
    section['box'] = box
    return box


def _ensure_square_symbol_section(normalized, section_name):
    section = normalized.get(section_name)
    if not isinstance(section, dict):
        return

    side = max(1, int(section.get('size', 64) or 64))
    default_box = {
        'x': int(section.get('x', 0) or 0),
        'y': int(section.get('y', 0) or 0),
        'width': side,
        'height': side,
    }
    box = _normalize_square_box(section, default_box)
    section['x'] = box['x']
    section['y'] = box['y']
    section['size'] = box['width']


def _ensure_square_coste_section(normalized):
    section = normalized.get('coste')
    if not isinstance(section, dict):
        return

    carta = normalized.get('carta') or {}
    card_width = int(carta.get('width', 745) or 745)
    card_height = int(carta.get('height', 1040) or 1040)
    side = max(1, int(section.get('size', 64) or 64))
    default_x = int(section.get('left', card_width - side - int(section.get('right', 40) or 40)))
    default_y = max(0, card_height - int(section.get('bottom', 40) or 40) - side)
    default_box = {
        'x': default_x,
        'y': default_y,
        'width': side,
        'height': side,
    }
    box = _normalize_square_box(section, default_box)
    section['size'] = box['width']
    section['bottom'] = max(0, card_height - box['y'] - box['height'])
    if 'right' in section:
        section['right'] = max(0, card_width - box['x'] - box['width'])
    if 'left' in section or 'right' not in section:
        section['left'] = box['x']


def normalize_layout_config(card_type, config):
    if not isinstance(config, dict):
        raise LayoutValidationError('config debe ser un objeto JSON')

    normalized_card_type = (card_type or '').strip().lower()
    if normalized_card_type not in ('cripta', 'libreria'):
        normalized_card_type = 'cripta'

    normalized = deepcopy(config)
    _ensure_text_v2_section(normalized, 'nombre')
    _ensure_text_v2_section(normalized, 'ilustrador')
    _ensure_square_symbol_section(normalized, 'clan')
    if normalized_card_type == 'cripta':
        _ensure_square_symbol_section(normalized, 'senda')
    _ensure_square_coste_section(normalized)
    return normalized


def _validate_box(section_name, section):
    box = section.get('box')
    if not isinstance(box, dict):
        raise LayoutValidationError(f'{section_name}.box debe ser un objeto')

    for field_name in ('x', 'y'):
        value = box.get(field_name)
        if not _is_number(value):
            raise LayoutValidationError(f'{section_name}.box.{field_name} debe ser numérico')
        if value < 0 or value > 3000:
            raise LayoutValidationError(f'{section_name}.box.{field_name} fuera de rango')

    for field_name in ('width', 'height'):
        value = box.get(field_name)
        if not _is_number(value):
            raise LayoutValidationError(f'{section_name}.box.{field_name} debe ser numérico')
        if value <= 0 or value > 3000:
            raise LayoutValidationError(f'{section_name}.box.{field_name} fuera de rango')


def _validate_text_rules(section_name, rules):
    if not isinstance(rules, dict):
        raise LayoutValidationError(f'{section_name}.rules debe ser un objeto')

    align = rules.get('align')
    if align not in ('left', 'center', 'right'):
        raise LayoutValidationError(f'{section_name}.rules.align inválido')

    anchor_mode = rules.get('anchor_mode')
    if anchor_mode not in ('free', 'top_locked', 'bottom_locked'):
        raise LayoutValidationError(f'{section_name}.rules.anchor_mode inválido')

    autoshrink = rules.get('autoshrink')
    if not isinstance(autoshrink, bool):
        raise LayoutValidationError(f'{section_name}.rules.autoshrink debe ser booleano')

    ellipsis_enabled = rules.get('ellipsis_enabled')
    if not isinstance(ellipsis_enabled, bool):
        raise LayoutValidationError(f'{section_name}.rules.ellipsis_enabled debe ser booleano')

    min_font_size = rules.get('min_font_size')
    if not _is_number(min_font_size):
        raise LayoutValidationError(f'{section_name}.rules.min_font_size debe ser numérico')
    if min_font_size < 8 or min_font_size > 200:
        raise LayoutValidationError(f'{section_name}.rules.min_font_size fuera de rango')


def validate_layout_config(card_type, config):
    if not isinstance(config, dict):
        raise LayoutValidationError('config debe ser un objeto JSON')

    normalized_card_type = (card_type or '').strip().lower()
    if normalized_card_type not in ('cripta', 'libreria'):
        raise LayoutValidationError('card_type inválido')
    normalized = normalize_layout_config(normalized_card_type, config)

    required_sections = ['carta', 'nombre', 'clan', 'disciplinas', 'habilidad', 'coste', 'ilustrador']
    if normalized_card_type == 'cripta':
        required_sections.extend(['senda', 'cripta'])
    else:
        required_sections.append('simbolos')

    for section in required_sections:
        _expect_dict(normalized, section)

    carta = normalized['carta']
    _expect_number(carta, 'width', 200, 3000)
    _expect_number(carta, 'height', 200, 3000)

    nombre = normalized['nombre']
    _expect_number(nombre, 'font_size', 8, 200)
    _expect_number(nombre, 'x', 0, 3000)
    y_value = nombre.get('y')
    if _is_number(y_value):
        if isinstance(y_value, float):
            if y_value < 0 or y_value > 1:
                raise LayoutValidationError('nombre.y fuera de rango')
        elif y_value < 0 or y_value > 3000:
            raise LayoutValidationError('nombre.y fuera de rango')
    else:
        raise LayoutValidationError('nombre.y debe ser numérico')
    _validate_box('nombre', nombre)
    _validate_text_rules('nombre', nombre.get('rules'))

    clan = normalized['clan']
    _expect_number(clan, 'size', 8, 1000)
    _expect_number(clan, 'x', 0, 3000)
    _expect_number(clan, 'y', 0, 3000)
    _validate_box('clan', clan)

    disciplinas = normalized['disciplinas']
    _expect_number(disciplinas, 'size', 8, 1000)
    _expect_number(disciplinas, 'x', 0, 3000)
    _expect_number(disciplinas, 'bottom', 0, 3000)
    _expect_number(disciplinas, 'spacing', 0, 1000)

    habilidad = normalized['habilidad']
    _expect_number(habilidad, 'font_size', 8, 200)
    _expect_number(habilidad, 'x', 0, 3000)
    _expect_ratio(habilidad, 'y_ratio')
    _expect_ratio(habilidad, 'max_width_ratio')
    if 'box_bottom_ratio' in habilidad:
        _expect_ratio(habilidad, 'box_bottom_ratio')
    _expect_number(habilidad, 'line_spacing', 0, 60)
    _expect_number(habilidad, 'bg_padding', 0, 300)
    _expect_number(habilidad, 'bg_radius', 0, 300)
    _validate_habilidad_box(habilidad)

    coste = normalized['coste']
    _expect_number(coste, 'size', 8, 300)
    _expect_number(coste, 'bottom', 0, 3000)
    if 'left' not in coste and 'right' not in coste:
        raise LayoutValidationError('coste debe incluir left o right')
    if 'left' in coste:
        _expect_number(coste, 'left', 0, 3000)
    if 'right' in coste:
        _expect_number(coste, 'right', 0, 3000)
    _validate_box('coste', coste)

    ilustrador = normalized['ilustrador']
    _expect_number(ilustrador, 'font_size', 8, 200)
    _expect_number(ilustrador, 'bottom', 0, 3000)
    _validate_box('ilustrador', ilustrador)
    _validate_text_rules('ilustrador', ilustrador.get('rules'))

    if normalized_card_type == 'cripta':
        senda = normalized['senda']
        _expect_number(senda, 'size', 8, 1000)
        _expect_number(senda, 'x', 0, 3000)
        _expect_number(senda, 'y', 0, 3000)
        _validate_box('senda', senda)

        cripta = normalized['cripta']
        _expect_number(cripta, 'font_size', 8, 200)
        _expect_number(cripta, 'y_gap', 0, 200)
    else:
        simbolos = normalized['simbolos']
        _expect_number(simbolos, 'size', 8, 1000)
        _expect_number(simbolos, 'x', 0, 3000)
        _expect_number(simbolos, 'y', 0, 3000)
        _expect_number(simbolos, 'spacing', 0, 1000)

    return normalized


def get_user_layout_config(request_user, card_type, layout_id=None):
    normalized_card_type = (card_type or '').strip().lower()
    if normalized_card_type not in ('cripta', 'libreria'):
        normalized_card_type = 'cripta'

    if layout_id is not None:
        selected = UserLayout.objects.filter(id=layout_id).first()
        if selected is None:
            return None
        if not request_user or not request_user.is_authenticated:
            raise LayoutOwnershipError('No autenticado')
        if selected.user_id != request_user.id:
            raise LayoutOwnershipError('Layout no pertenece al usuario')
        if selected.card_type != normalized_card_type:
            raise LayoutValidationError('layout_id no coincide con card_type')
        return deepcopy(selected.config)

    if request_user and request_user.is_authenticated:
        default_layout = UserLayout.objects.filter(
            user=request_user,
            card_type=normalized_card_type,
            is_default=True,
        ).first()
        if default_layout:
            return deepcopy(default_layout.config)
    return None
