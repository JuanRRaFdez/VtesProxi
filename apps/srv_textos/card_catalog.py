import json
import os
import re
import unicodedata
from typing import Dict, List, Optional

from django.conf import settings


_VALID_CARD_TYPES = {'cripta', 'libreria'}
_DISCIPLINE_CODES = {
    'abo', 'ani', 'aus', 'cel', 'chi', 'dai', 'def', 'dem', 'dom', 'flight', 'for',
    'inn', 'jus', 'mal', 'mar', 'mel', 'myt', 'nec', 'obe', 'obf', 'obl', 'obt',
    'pot', 'pre', 'pro', 'qui', 'red', 'san', 'ser', 'spi', 'str', 'tem', 'tha',
    'thn', 'val', 'ven', 'vic', 'vin', 'vis',
}
_DISC_NO_SUP = {'def', 'flight', 'inn', 'jus', 'mar', 'red', 'ven', 'vin'}
_DISC_ALIASES = {
    'jud': 'jus',
    'viz': 'vin',
}
_ICON_ORDER = [
    'action', 'modifier', 'reaction', 'combat', 'political', 'ally', 'retainer',
    'equipment', 'event', 'master', 'burn', 'merged', 'adv', 'directed',
]

_CATALOG_CACHE: Dict[str, List[dict]] = {'cripta': [], 'libreria': []}
_CATALOG_INDEX: Dict[str, Dict[str, dict]] = {'cripta': {}, 'libreria': {}}
_CATALOG_MTIME: Dict[str, Optional[float]] = {'cripta': None, 'libreria': None}


def normalize_text(text: str) -> str:
    raw = str(text or '')
    decomposed = unicodedata.normalize('NFD', raw)
    without_accents = ''.join(ch for ch in decomposed if not unicodedata.combining(ch))
    lowered = without_accents.lower()
    collapsed = re.sub(r'\s+', ' ', lowered).strip()
    return collapsed


def _simplify_token(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', normalize_text(text))


def _get_json_path(card_type: str) -> str:
    if card_type == 'cripta':
        return os.path.join(settings.BASE_DIR, 'Cripta_2.json')
    return os.path.join(settings.BASE_DIR, 'Libreria_2.json')


def _load_catalog(card_type: str) -> None:
    path = _get_json_path(card_type)
    if not os.path.exists(path):
        _CATALOG_CACHE[card_type] = []
        _CATALOG_INDEX[card_type] = {}
        _CATALOG_MTIME[card_type] = None
        return

    mtime = os.path.getmtime(path)
    if _CATALOG_MTIME[card_type] == mtime:
        return

    with open(path, encoding='utf-8') as fh:
        cards = json.load(fh)

    entries = []
    index = {}
    for card in cards:
        name = (card.get('Name') or '').strip()
        if not name:
            continue
        name_norm = normalize_text(name)
        card_copy = dict(card)
        card_copy['_name_norm'] = name_norm
        entries.append(card_copy)
        if name_norm and name_norm not in index:
            index[name_norm] = card_copy

    _CATALOG_CACHE[card_type] = entries
    _CATALOG_INDEX[card_type] = index
    _CATALOG_MTIME[card_type] = mtime


def _ensure_catalog_loaded(card_type: str) -> bool:
    if card_type not in _VALID_CARD_TYPES:
        return False
    _load_catalog(card_type)
    return True


def _available_clan_files() -> List[str]:
    clan_dir = os.path.join(settings.BASE_DIR, 'static', 'clan_symbols')
    if not os.path.isdir(clan_dir):
        return []
    return sorted([fname for fname in os.listdir(clan_dir) if fname.lower().endswith('.png')])


def _available_icon_bases() -> List[str]:
    icons_dir = os.path.join(settings.BASE_DIR, 'static', 'icons')
    if not os.path.isdir(icons_dir):
        return []
    bases = set()
    for fname in os.listdir(icons_dir):
        lower = fname.lower()
        if not (lower.endswith('.png') or lower.endswith('.svg')):
            continue
        bases.add(lower.rsplit('.', 1)[0])
    return sorted(bases)


def _resolve_clan_file(clan_value: str, available_clan_files: List[str]) -> str:
    if not clan_value:
        return ''

    clan_lookup = {}
    for fname in available_clan_files:
        base = fname.rsplit('.', 1)[0]
        clan_lookup[_simplify_token(base)] = fname

    segments = [segment.strip() for segment in str(clan_value).split('/') if segment.strip()]
    if not segments:
        segments = [str(clan_value).strip()]

    for segment in segments:
        match = clan_lookup.get(_simplify_token(segment))
        if match:
            return match
    return ''


def _normalize_discipline_token(token: str) -> Optional[tuple]:
    raw = (token or '').strip()
    if not raw or raw == '&':
        return None

    superior = raw.isupper() and len(raw) > 1
    normalized = _DISC_ALIASES.get(raw.lower(), raw.lower())

    if normalized not in _DISCIPLINE_CODES:
        return None

    level = 'sup' if superior and normalized not in _DISC_NO_SUP else 'inf'
    return normalized, level


def _parse_disciplines(raw_value: str) -> List[dict]:
    parts = re.split(r'[\s/]+', str(raw_value or '').strip())
    states = {}
    for part in parts:
        info = _normalize_discipline_token(part)
        if not info:
            continue
        code, level = info
        current = states.get(code)
        if current == 'sup':
            continue
        if current is None:
            states[code] = level
        elif current == 'inf' and level == 'sup':
            states[code] = 'sup'

    return [{'name': code, 'level': level} for code, level in states.items()]


def _build_libreria_symbols(type_value: str, text_value: str, available_icons: List[str]) -> List[str]:
    if not available_icons:
        return []

    available = set()
    for icon in available_icons:
        base = str(icon or '').strip().lower()
        if not base:
            continue
        if base.endswith('.png') or base.endswith('.svg'):
            base = base.rsplit('.', 1)[0]
        available.add(base)

    found = set()
    segments = [normalize_text(seg) for seg in str(type_value or '').split('/') if seg.strip()]
    for seg in segments:
        if 'action modifier' in seg:
            found.add('modifier')
            continue
        if 'political action' in seg:
            found.add('political')
            continue
        if seg == 'action':
            found.add('action')
            continue
        if 'reaction' in seg:
            found.add('reaction')
        if 'combat' in seg:
            found.add('combat')
        if 'equipment' in seg:
            found.add('equipment')
        if 'event' in seg:
            found.add('event')
        if 'master' in seg:
            found.add('master')
        if 'ally' in seg:
            found.add('ally')
        if 'retainer' in seg:
            found.add('retainer')
        if 'burn' in seg:
            found.add('burn')
        if 'merged' in seg:
            found.add('merged')
        if seg == 'advanced':
            found.add('adv')

    text_norm = normalize_text(text_value)
    if '(d)' in text_norm or 'Ⓓ' in str(text_value or ''):
        found.add('directed')

    return [icon for icon in _ICON_ORDER if icon in found and icon in available]


def _to_libreria_cost(prefix: str, raw_value: str) -> str:
    value = str(raw_value or '').strip()
    if not value:
        return ''
    if value.upper() == 'X':
        return f'{prefix}x'
    if value.isdigit():
        return f'{prefix}{value}'
    return ''


def map_card_to_form_payload(
    card_type: str,
    card: dict,
    available_clan_files: Optional[List[str]] = None,
    available_icons: Optional[List[str]] = None,
) -> dict:
    card_type = (card_type or 'cripta').strip().lower()
    clan_files = _available_clan_files() if available_clan_files is None else list(available_clan_files)
    icon_files = _available_icon_bases() if available_icons is None else list(available_icons)

    payload = {
        'nombre': (card.get('Name') or '').strip(),
        'clan': _resolve_clan_file(card.get('Clan') or '', clan_files),
        'senda': '',
        'coste': '',
        'cripta': '',
        'ilustrador': '',
        'habilidad': (card.get('Text') or '').strip(),
        'disciplinas': _parse_disciplines(card.get('Discipline') or ''),
        'simbolos': [],
    }

    if card_type == 'libreria':
        pool_cost = _to_libreria_cost('pool', card.get('PoolCost') or '')
        blood_cost = _to_libreria_cost('blood', card.get('BloodCost') or '')
        payload['coste'] = pool_cost or blood_cost
        payload['simbolos'] = _build_libreria_symbols(
            type_value=card.get('Type') or '',
            text_value=card.get('Text') or '',
            available_icons=icon_files,
        )
    else:
        capacity = str(card.get('Capacity') or '').strip()
        group = str(card.get('Group') or '').strip()
        payload['coste'] = capacity if capacity.isdigit() and 1 <= int(capacity) <= 11 else ''
        payload['cripta'] = group if group.isdigit() and 1 <= int(group) <= 9 else ''

    return payload


def search_card_suggestions(card_type: str, query: str, limit: int = 10) -> List[dict]:
    card_type = (card_type or '').strip().lower()
    if not _ensure_catalog_loaded(card_type):
        return []

    query_norm = normalize_text(query)
    if not query_norm:
        return []

    safe_limit = max(1, min(int(limit or 10), 25))
    results = []
    for card in _CATALOG_CACHE[card_type]:
        if query_norm in card.get('_name_norm', ''):
            results.append({'name': card.get('Name', '')})
            if len(results) >= safe_limit:
                break
    return results


def get_card_autocomplete(card_type: str, name: str) -> Optional[dict]:
    card_type = (card_type or '').strip().lower()
    if not _ensure_catalog_loaded(card_type):
        return None

    normalized_name = normalize_text(name)
    if not normalized_name:
        return None

    card = _CATALOG_INDEX[card_type].get(normalized_name)
    if not card:
        return None
    return map_card_to_form_payload(card_type=card_type, card=card)
