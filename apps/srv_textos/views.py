from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
import os
import json
import shutil
from PIL import Image, ImageDraw, ImageFont
from django.utils.crypto import get_random_string


def _load_layout():
    """Carga el layout activo desde layouts.json."""
    json_path = os.path.join(os.path.dirname(__file__), 'layouts.json')
    with open(json_path, encoding='utf-8') as f:
        data = json.load(f)
    active = data['active']
    layout = data['layouts'].get(active)
    if layout is None:
        raise KeyError(f"Layout '{active}' no encontrado en layouts.json")
    return layout


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
    2. Después de ':' hasta el primer '.' (fuera de paréntesis) → normal
       - Texto entre paréntesis '()' → italic
    3. Después de ese '.' → bold
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

    # Encontrar el primer '.' fuera de paréntesis
    dot_idx = None
    paren_depth = 0
    for i, ch in enumerate(rest):
        if ch == '(':
            paren_depth += 1
        elif ch == ')':
            paren_depth = max(0, paren_depth - 1)
        elif ch == '.' and paren_depth == 0:
            dot_idx = i
            break

    if dot_idx is not None:
        normal_section = rest[:dot_idx + 1]
        bold_tail = rest[dot_idx + 1:]
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


# --- Helper: renderiza texto con word-wrap y múltiples estilos ---
def _render_habilidad_text(image, text, x, y, max_width, font_size, color, bg_opacity=180,
                           bg_padding=10, bg_radius=12, line_spacing=3, bg_color=(0, 0, 0),
                           box_height=None):
    """Renderiza el texto de habilidad con formato mixto, word-wrap y fondo redondeado."""
    font_bold, font_normal = _load_hab_fonts(font_size)
    segments = _parse_habilidad(text)
    if not segments:
        return

    # --- Primer paso: calcular dimensiones del texto (dry run) ---
    words = []
    for seg in segments:
        style = seg['style']
        font = font_bold if style == 'bold' else font_normal
        parts = seg['text'].split(' ')
        for idx, part in enumerate(parts):
            if idx > 0:
                part = ' ' + part
            if part:
                words.append({'text': part, 'style': style, 'font': font})

    line_height = font_size + line_spacing
    cur_x = x
    cur_y = y
    max_right = x
    for word_info in words:
        w_text = word_info['text']
        w_font = word_info['font']
        bbox = w_font.getbbox(w_text)
        w_width = bbox[2] - bbox[0]
        if cur_x + w_width > x + max_width - bg_padding and cur_x > x:
            cur_x = x
            cur_y += line_height
            if w_text.startswith(' '):
                w_text = w_text.lstrip(' ')
                bbox = w_font.getbbox(w_text)
                w_width = bbox[2] - bbox[0]
        if cur_x + w_width > max_right:
            max_right = cur_x + w_width
        cur_x += w_width

    text_bottom = cur_y + line_height
    text_right = x + max_width

    # --- Dibujar recuadro redondeado con transparencia ---
    pad = bg_padding
    rx, ry = x - pad, y - pad * 2
    rw = text_right - x + pad
    # Altura fija si se especifica box_height, dinámica si no
    if box_height is not None:
        rh = box_height
    else:
        rh = text_bottom - y + pad
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
    text_width = max_width - pad
    lines = []
    current_line = []
    cur_x = x
    for word_info in words:
        w_text = word_info['text']
        w_font = word_info['font']
        w_style = word_info['style']
        bbox = w_font.getbbox(w_text)
        w_width = bbox[2] - bbox[0]
        if cur_x + w_width > x + text_width and cur_x > x:
            lines.append(current_line)
            current_line = []
            cur_x = x
            if w_text.startswith(' '):
                w_text = w_text.lstrip(' ')
                bbox = w_font.getbbox(w_text)
                w_width = bbox[2] - bbox[0]
        current_line.append({'text': w_text, 'style': w_style, 'font': w_font})
        cur_x += w_width
    if current_line:
        lines.append(current_line)

    # --- Tercer paso: dibujar líneas con justificado ---
    draw = ImageDraw.Draw(image)
    cur_y = y - int(pad * 1.5)
    for line_idx, line in enumerate(lines):
        is_last_line = (line_idx == len(lines) - 1)
        # Calcular ancho de cada palabra (sin espacio inicial)
        stripped_words = [winfo['text'].lstrip(' ') for winfo in line]
        word_widths = []
        for i, winfo in enumerate(line):
            bbox = winfo['font'].getbbox(stripped_words[i])
            word_widths.append(bbox[2] - bbox[0])
        total_word_width = sum(word_widths)
        num_words = len(line)
        if is_last_line or num_words <= 1:
            # Última línea: alinear a la izquierda con espacio normal
            cur_x = x
            for i, winfo in enumerate(line):
                t = stripped_words[i]
                if winfo['style'] == 'italic':
                    _draw_italic(image, int(cur_x), cur_y, t, winfo['font'], color, font_size)
                else:
                    draw.text((int(cur_x), cur_y), t, font=winfo['font'], fill=color)
                cur_x += word_widths[i]
                if i < num_words - 1:
                    sp = winfo['font'].getbbox(' ')
                    cur_x += sp[2] - sp[0]
        else:
            # Justificado: distribuir espacio extra entre palabras
            gaps = num_words - 1
            space_per_gap = (text_width - total_word_width) / gaps
            cur_x = x
            for i, winfo in enumerate(line):
                t = stripped_words[i]
                if winfo['style'] == 'italic':
                    _draw_italic(image, int(cur_x), cur_y, t, winfo['font'], color, font_size)
                else:
                    draw.text((int(cur_x), cur_y), t, font=winfo['font'], fill=color)
                cur_x += word_widths[i]
                if i < num_words - 1:
                    cur_x += space_per_gap
        cur_y += line_height


def _draw_italic(image, x, y, text, font, color, font_size):
    """Simula texto en cursiva usando transformación de cizalla (shear)."""
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
        (1, -shear, shear * h / 2, 0, 1, 0),
        resample=Image.BICUBIC
    )
    image.alpha_composite(tmp, (x, y))


# --- Helper principal: renderiza TODOS los elementos sobre la imagen base ---
def _render_carta(imagen_url, nombre='', clan='', senda='', disciplinas=None, habilidad='', coste='', cripta='', ilustrador='', hab_opacity=180):
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

    lay = _load_layout()
    lc  = lay['carta']
    ln  = lay['nombre']
    lcl = lay['clan']
    ls  = lay['senda']
    ld  = lay['disciplinas']
    lh  = lay['habilidad']
    lco = lay['coste']
    lcr = lay['cripta']
    lil = lay['ilustrador']

    card_w = lc['width']
    card_h = lc['height']

    image = Image.open(imagen_abspath).convert('RGBA')
    image = image.resize((card_w, card_h), Image.LANCZOS)

    # --- Variables locales desde el layout activo ---
    clan_size    = lcl['size']
    clan_x       = lcl['x']
    clan_y       = lcl['y']

    senda_size   = ls['size']
    senda_x      = ls['x']
    senda_y      = ls['y']

    disc_size    = ld['size']
    disc_x       = ld['x']
    disc_bottom  = ld['bottom']
    disc_spacing = ld['spacing']

    hab_font_size = lh['font_size']
    hab_x         = lh['x']
    hab_y         = int(card_h * lh['y_ratio'])
    hab_max_w     = int(card_w * lh['max_width_ratio'])
    hab_padding   = lh['bg_padding']
    hab_radius    = lh['bg_radius']
    hab_line_sp   = lh['line_spacing']
    hab_box_h     = int(card_h * lh['box_bottom_ratio']) - hab_y if 'box_bottom_ratio' in lh else None

    coste_size   = lco['size']
    coste_right  = lco['right']
    coste_bottom = lco['bottom']

    cripta_font_size = lcr['font_size']
    cripta_y_gap     = lcr['y_gap']

    il_font_size = lil['font_size']
    il_bottom    = lil['bottom']

    # 1) Nombre (independiente de los símbolos)
    if nombre:
        font_path = os.path.join(settings.BASE_DIR, ln['font_path'])
        if not os.path.exists(font_path):
            raise FileNotFoundError(f"No se encontró la fuente en {font_path}")
        font = ImageFont.truetype(font_path, ln['font_size'])
        draw = ImageDraw.Draw(image)

        x = ln['x']
        y_cfg = ln['y']
        y = int(image.height * y_cfg) if isinstance(y_cfg, float) else int(y_cfg)

        shadow = ln.get('shadow', {})
        if shadow.get('enabled', False):
            for dx, dy in shadow.get('offsets', []):
                draw.text((x + dx, y + dy), nombre, font=font, fill=shadow.get('color', 'black'))
        draw.text((x, y), nombre, font=font, fill=ln.get('color', 'white'))

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
    if senda:
        senda_symbol_path = os.path.join(settings.BASE_DIR, 'static/path', senda)
        if os.path.exists(senda_symbol_path):
            try:
                senda_img = _load_symbol(senda_symbol_path, senda_size)
                image.alpha_composite(senda_img, (senda_x, senda_y))
            except Exception as e:
                print(f'Error renderizando símbolo de senda: {e}')
        else:
            print(f"[DEBUG] Archivo de senda no encontrado: {senda_symbol_path}")

    # 4) Disciplinas (columna vertical: disc_sup abajo, disc_inf encima)
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
            y_bottom = image.height - disc_bottom - disc_size
            for disc_img in all_discs:
                image.alpha_composite(disc_img, (disc_x, y_bottom))
                y_bottom -= disc_spacing

    # Base Y del recuadro de habilidad (se computa siempre)
    pad = hab_padding

    # 5) Número de cripta (sobre el recuadro, pegado a la izquierda)
    if cripta:
        try:
            font_bold, _ = _load_hab_fonts(cripta_font_size)
            box_top = hab_y - pad * 2
            cripta_y = box_top - cripta_font_size - cripta_y_gap
            cripta_x = hab_x - pad
            draw_cripta = ImageDraw.Draw(image)
            draw_cripta.text((cripta_x, cripta_y), str(cripta), font=font_bold, fill=lcr['color'])
        except Exception as e:
            print(f'Error renderizando cripta: {e}')

    # 6) Habilidad (cuadro de texto con formato mixto)
    if habilidad:
        try:
            _render_habilidad_text(image, habilidad, hab_x, hab_y, hab_max_w, hab_font_size, lh['color'],
                                   bg_opacity=hab_opacity, bg_padding=hab_padding,
                                   bg_radius=hab_radius, line_spacing=hab_line_sp,
                                   bg_color=tuple(lh['bg_color']), box_height=hab_box_h)
        except Exception as e:
            print(f'Error renderizando habilidad: {e}')

    # 7) Ilustrador (centrado, pegado a la parte inferior de la carta)
    if ilustrador:
        try:
            _, font_normal = _load_hab_fonts(il_font_size)
            il_bbox = font_normal.getbbox(ilustrador)
            il_w = il_bbox[2] - il_bbox[0]
            il_h = il_bbox[3] - il_bbox[1]
            il_x = (image.width - il_w) // 2
            il_y = image.height - il_h - il_bottom
            draw_il = ImageDraw.Draw(image)
            draw_il.text((il_x, il_y), ilustrador, font=font_normal, fill=lil['color'])
        except Exception as e:
            print(f'Error renderizando ilustrador: {e}')

    # 8) Coste (símbolo abajo a la derecha)
    print(f'[DEBUG] coste recibido: "{coste}" (type={type(coste).__name__})')
    if coste:
        coste_file = f'cap{coste}.gif'
        coste_path = os.path.join(settings.BASE_DIR, 'static/costes', coste_file)
        print(f'[DEBUG] coste_path: {coste_path}, exists: {os.path.exists(coste_path)}')
        if os.path.exists(coste_path):
            try:
                coste_img = Image.open(coste_path).convert('RGBA')
                coste_img = coste_img.resize((coste_size, coste_size), Image.LANCZOS)
                coste_x = image.width - coste_right - coste_size
                coste_y = image.height - coste_bottom - coste_size
                image.alpha_composite(coste_img, (coste_x, coste_y))
            except Exception as e:
                print(f'Error renderizando coste: {e}')
        else:
            print(f'[DEBUG] Archivo de coste no encontrado: {coste_path}')

    # Guardar imagen renderizada
    render_dir = os.path.join(settings.MEDIA_ROOT, 'render')
    os.makedirs(render_dir, exist_ok=True)
    filename = f'render_{get_random_string(8)}.png'
    render_path = os.path.join(render_dir, filename)
    image.save(render_path, 'PNG')
    render_url = settings.MEDIA_URL + 'render/' + filename
    return render_url, None


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
        habilidad = (data.get('habilidad') or '').strip()
        coste = (data.get('coste') or '').strip()
        cripta = str(data.get('cripta') or '').strip()
        ilustrador = (data.get('ilustrador') or '').strip()
        hab_opacity = int(data.get('hab_opacity', 180))
        imagen_url = data.get('imagen_url', '')
        if not imagen_url:
            return JsonResponse({'error': 'Faltan datos'}, status=400)

        render_url, error = _render_carta(imagen_url, nombre=nombre, clan=clan, senda=senda, disciplinas=disciplinas, habilidad=habilidad, coste=coste, cripta=cripta, ilustrador=ilustrador, hab_opacity=hab_opacity)
        if error:
            return JsonResponse({'error': error}, status=404)
        return JsonResponse({'imagen_url': render_url})
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
        habilidad = (data.get('habilidad') or '').strip()
        coste = (data.get('coste') or '').strip()
        cripta = str(data.get('cripta') or '').strip()
        ilustrador = (data.get('ilustrador') or '').strip()
        hab_opacity = int(data.get('hab_opacity', 180))
        imagen_url = data.get('imagen_url', '')
        if not imagen_url:
            return JsonResponse({'error': 'Faltan datos'}, status=400)

        render_url, error = _render_carta(imagen_url, nombre=nombre, clan=clan, senda=senda, disciplinas=disciplinas, habilidad=habilidad, coste=coste, cripta=cripta, ilustrador=ilustrador, hab_opacity=hab_opacity)
        if error:
            return JsonResponse({'error': error}, status=404)
        return JsonResponse({'imagen_url': render_url})
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
        habilidad = (data.get('habilidad') or '').strip()
        coste = (data.get('coste') or '').strip()
        cripta = str(data.get('cripta') or '').strip()
        ilustrador = (data.get('ilustrador') or '').strip()
        hab_opacity = int(data.get('hab_opacity', 180))
        imagen_url = data.get('imagen_url', '')
        if not imagen_url:
            return JsonResponse({'error': 'Faltan datos'}, status=400)

        render_url, error = _render_carta(imagen_url, nombre=nombre, clan=clan, senda=senda, disciplinas=disciplinas, habilidad=habilidad, coste=coste, cripta=cripta, ilustrador=ilustrador, hab_opacity=hab_opacity)
        if error:
            return JsonResponse({'error': error}, status=404)
        return JsonResponse({'imagen_url': render_url})
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
        if not render_url:
            return JsonResponse({'error': 'Falta render_url'}, status=400)

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

        filename = f'carta_{get_random_string(10)}.png'
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
