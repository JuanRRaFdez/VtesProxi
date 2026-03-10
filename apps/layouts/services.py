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
