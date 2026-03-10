import json
from copy import deepcopy
from pathlib import Path


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


def validate_layout_config(card_type, config):
    if not isinstance(config, dict):
        raise LayoutValidationError('config debe ser un objeto JSON')

    normalized = deepcopy(config)
    normalized_card_type = (card_type or '').strip().lower()
    if normalized_card_type not in ('cripta', 'libreria'):
        raise LayoutValidationError('card_type inválido')

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

    clan = normalized['clan']
    _expect_number(clan, 'size', 8, 1000)
    _expect_number(clan, 'x', 0, 3000)
    _expect_number(clan, 'y', 0, 3000)

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

    ilustrador = normalized['ilustrador']
    _expect_number(ilustrador, 'font_size', 8, 200)
    _expect_number(ilustrador, 'bottom', 0, 3000)

    if normalized_card_type == 'cripta':
        senda = normalized['senda']
        _expect_number(senda, 'size', 8, 1000)
        _expect_number(senda, 'x', 0, 3000)
        _expect_number(senda, 'y', 0, 3000)

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
