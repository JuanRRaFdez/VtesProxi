from copy import deepcopy
import json
import os
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from apps.layouts.models import UserLayout
from apps.layouts.services import load_classic_seed, normalize_layout_config
from apps.srv_textos import card_catalog
from apps.srv_textos import views as srv_textos_views


class CardCatalogHelpersTests(SimpleTestCase):
    def test_normalize_text_ignores_case_and_accents(self):
        self.assertEqual(card_catalog.normalize_text('ÁrIkA'), 'arika')
        self.assertEqual(card_catalog.normalize_text('Nosferatú antitribu'), 'nosferatu antitribu')

    def test_map_card_to_form_payload_for_cripta(self):
        card = {
            'Name': 'Arika',
            'Clan': 'Ventrue',
            'Discipline': 'aus DOM',
            'Text': 'Inner Circle text.',
            'Capacity': '11',
            'Group': '6',
            'PoolCost': '',
            'BloodCost': '',
            'Type': 'Vampire',
        }

        payload = card_catalog.map_card_to_form_payload(
            card_type='cripta',
            card=card,
            available_clan_files=['ventrue.png'],
            available_icons=[],
        )

        self.assertEqual(payload['nombre'], 'Arika')
        self.assertEqual(payload['clan'], 'ventrue.png')
        self.assertEqual(payload['coste'], '11')
        self.assertEqual(payload['cripta'], '6')
        self.assertEqual(payload['habilidad'], 'Inner Circle text.')
        self.assertEqual(payload['disciplinas'], [
            {'name': 'aus', 'level': 'inf'},
            {'name': 'dom', 'level': 'sup'},
        ])

    def test_map_card_to_form_payload_for_libreria(self):
        card = {
            'Name': 'Govern the Unaligned',
            'Clan': 'Ventrue',
            'Discipline': 'dom',
            'Text': '[dom] (D) Bleed with +2 bleed.',
            'Capacity': '',
            'Group': '',
            'PoolCost': '1',
            'BloodCost': '',
            'Type': 'Action/Reaction',
        }

        payload = card_catalog.map_card_to_form_payload(
            card_type='libreria',
            card=card,
            available_clan_files=['ventrue.png'],
            available_icons=['action.png', 'reaction.png', 'directed.png'],
        )

        self.assertEqual(payload['nombre'], 'Govern the Unaligned')
        self.assertEqual(payload['clan'], 'ventrue.png')
        self.assertEqual(payload['coste'], 'pool1')
        self.assertEqual(payload['cripta'], '')
        self.assertEqual(payload['habilidad'], '[dom] (D) Bleed with +2 bleed.')
        self.assertEqual(payload['disciplinas'], [
            {'name': 'dom', 'level': 'inf'},
        ])
        self.assertEqual(payload['simbolos'], ['action', 'reaction', 'directed'])


class CardCatalogViewsTests(TestCase):
    def test_buscar_cartas_uses_default_limit(self):
        with patch('apps.srv_textos.views.search_card_suggestions', return_value=[{'name': 'Arika'}]) as mock_search:
            response = self.client.get('/srv-textos/buscar-cartas/', {
                'card_type': 'cripta',
                'q': 'Ári',
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'results': [{'name': 'Arika'}]})
        mock_search.assert_called_once_with('cripta', 'Ári', limit=10)

    def test_buscar_cartas_short_query_returns_empty(self):
        response = self.client.get('/srv-textos/buscar-cartas/', {
            'card_type': 'cripta',
            'q': 'a',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'results': []})

    def test_autocompletar_carta_returns_payload(self):
        payload = {'nombre': 'Arika', 'coste': '11'}
        with patch('apps.srv_textos.views.get_card_autocomplete', return_value=payload) as mock_get:
            response = self.client.get('/srv-textos/autocompletar-carta/', {
                'card_type': 'cripta',
                'name': 'Arika',
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'card': payload})
        mock_get.assert_called_once_with('cripta', 'Arika')

    def test_autocompletar_carta_not_found(self):
        with patch('apps.srv_textos.views.get_card_autocomplete', return_value=None):
            response = self.client.get('/srv-textos/autocompletar-carta/', {
                'card_type': 'cripta',
                'name': 'No existe',
            })

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'Carta no encontrada'})


class LayoutResolverPriorityTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='resolver-user', password='secret')
        self.other_user = user_model.objects.create_user(username='resolver-other', password='secret')

    def test_render_uses_layout_override_first(self):
        selected_layout = UserLayout.objects.get(
            user=self.user,
            card_type='cripta',
            is_default=True,
        )
        override = deepcopy(load_classic_seed('cripta'))
        override['carta']['width'] = 1234

        resolved = srv_textos_views._resolve_layout_config(
            request_user=self.user,
            card_type='cripta',
            layout_id=selected_layout.id,
            layout_override=override,
        )

        self.assertEqual(resolved['carta']['width'], 1234)

    def test_render_uses_layout_id_when_provided(self):
        default_layout = load_classic_seed('cripta')
        default_layout['carta']['width'] = 800
        selected_layout = load_classic_seed('cripta')
        selected_layout['carta']['width'] = 950

        default = UserLayout.objects.get(user=self.user, card_type='cripta', is_default=True)
        default.config = default_layout
        default.save(update_fields=['config'])
        selected = UserLayout.objects.create(
            user=self.user,
            name='Seleccionado',
            card_type='cripta',
            config=selected_layout,
            is_default=False,
        )

        resolved = srv_textos_views._resolve_layout_config(
            request_user=self.user,
            card_type='cripta',
            layout_id=selected.id,
        )

        self.assertEqual(resolved['carta']['width'], 950)

    def test_render_rejects_layout_id_from_other_user(self):
        other_layout = UserLayout.objects.create(
            user=self.other_user,
            name='Ajeno',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

        with self.assertRaises(PermissionError):
            srv_textos_views._resolve_layout_config(
                request_user=self.user,
                card_type='cripta',
                layout_id=other_layout.id,
            )


class ImportViewsLayoutContextTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='import-user', password='secret')
        self.other_user = user_model.objects.create_user(username='import-other', password='secret')

        self.cripta_default = UserLayout.objects.get(
            user=self.user,
            card_type='cripta',
            is_default=True,
        )
        self.cripta_alt = UserLayout.objects.create(
            user=self.user,
            name='Cripta alt',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )
        self.libreria_default = UserLayout.objects.get(
            user=self.user,
            card_type='libreria',
            is_default=True,
        )

    def test_cripta_view_uses_user_layout_options(self):
        self.client.force_login(self.user)
        response = self.client.get('/cripta/importar-imagen/')

        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['card_type'], 'cripta')
        self.assertEqual(context['active_layout_id'], self.cripta_default.id)

        option_ids = sorted([item['id'] for item in context['layout_options']])
        self.assertEqual(option_ids, sorted([self.cripta_default.id, self.cripta_alt.id]))

    def test_libreria_view_uses_user_layout_options(self):
        self.client.force_login(self.user)
        response = self.client.get('/libreria/importar-imagen/')

        self.assertEqual(response.status_code, 200)
        context = response.context
        self.assertEqual(context['card_type'], 'libreria')
        self.assertEqual(context['active_layout_id'], self.libreria_default.id)
        self.assertEqual(len(context['layout_options']), 1)
        self.assertEqual(context['layout_options'][0]['id'], self.libreria_default.id)


class TextInBoxHelpersTests(SimpleTestCase):
    def test_fit_text_shrinks_then_ellipsis(self):
        fitted = srv_textos_views._fit_text_to_box(
            text='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            font_path='static/fonts/MatrixExtraBold.otf',
            start_font_size=50,
            min_font_size=18,
            max_width=80,
            ellipsis_enabled=True,
        )

        self.assertLessEqual(fitted['width'], 80)
        self.assertTrue(fitted['text'].endswith('...'))

    def test_horizontal_alignment_center(self):
        x = srv_textos_views._compute_aligned_x(100, 40, 'center')

        self.assertEqual(x, 130)


class HabilidadRenderAlignmentTests(SimpleTestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_render_habilidad_libreria_uses_same_common_renderer_path_as_cripta(self):
        image_path = os.path.join(settings.MEDIA_ROOT, 'recortes', 'test.png')
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        Image.new('RGBA', (745, 1040), (0, 0, 0, 0)).save(image_path)
        common_calls = []

        def fake_common_renderer(*args, **kwargs):
            common_calls.append((args, kwargs))

        with patch('apps.srv_textos.views._render_habilidad_text', side_effect=fake_common_renderer), patch(
            'apps.srv_textos.views._render_habilidad_text_libreria'
        ) as mock_libreria_renderer:
            srv_textos_views._render_carta(
                imagen_url='/media/recortes/test.png',
                habilidad='Texto de prueba',
                card_type='libreria',
                layout_config=normalize_layout_config('libreria', load_classic_seed('libreria')),
            )

        self.assertEqual(len(common_calls), 1)
        mock_libreria_renderer.assert_not_called()

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_render_habilidad_libreria_bottom_anchor_margin_passes_bottom_anchored_box_to_common_renderer(self):
        image_path = os.path.join(settings.MEDIA_ROOT, 'recortes', 'test-bottom-anchor.png')
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        Image.new('RGBA', (745, 1040), (0, 0, 0, 0)).save(image_path)
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['box'] = {
            'x': 170,
            'y': 820,
            'width': 420,
            'height': 24,
        }

        with patch('apps.srv_textos.views._render_habilidad_text') as mock_render:
            srv_textos_views._render_carta(
                imagen_url='/media/recortes/test-bottom-anchor.png',
                habilidad='Texto de prueba suficientemente largo para ocupar varias lineas dentro del cuadro de habilidad.',
                card_type='libreria',
                layout_config=config,
            )

        self.assertEqual(mock_render.call_count, 1)
        _, _, hab_x, hab_y, hab_max_w, _, _ = mock_render.call_args.args[:7]
        self.assertEqual(hab_x, 170)
        self.assertEqual(hab_max_w, 420)
        self.assertLess(hab_y, 820)
        self.assertEqual(hab_y + mock_render.call_args.kwargs['box_height'], 820)
        self.assertEqual(mock_render.call_args.kwargs['vertical_padding'], 24)

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_render_habilidad_libreria_bottom_anchor_margin_grows_with_effective_font_size(self):
        image_path = os.path.join(settings.MEDIA_ROOT, 'recortes', 'test-bottom-anchor-font.png')
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        Image.new('RGBA', (745, 1040), (0, 0, 0, 0)).save(image_path)
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['box'] = {
            'x': 170,
            'y': 820,
            'width': 420,
            'height': 24,
        }
        habilidad = 'Texto de habilidad suficientemente largo para notar el crecimiento del recuadro.'

        with patch('apps.srv_textos.views._render_habilidad_text') as small_render:
            srv_textos_views._render_carta(
                imagen_url='/media/recortes/test-bottom-anchor-font.png',
                habilidad=habilidad,
                card_type='libreria',
                layout_config=config,
                hab_font_size=20,
            )

        with patch('apps.srv_textos.views._render_habilidad_text') as large_render:
            srv_textos_views._render_carta(
                imagen_url='/media/recortes/test-bottom-anchor-font.png',
                habilidad=habilidad,
                card_type='libreria',
                layout_config=config,
                hab_font_size=48,
            )

        self.assertGreater(
            large_render.call_args.kwargs['box_height'],
            small_render.call_args.kwargs['box_height'],
        )
        self.assertEqual(
            small_render.call_args.args[3] + small_render.call_args.kwargs['box_height'],
            820,
        )
        self.assertEqual(
            large_render.call_args.args[3] + large_render.call_args.kwargs['box_height'],
            820,
        )

    def test_parse_habilidad_defaults_plain_text_to_normal(self):
        segments = srv_textos_views._parse_habilidad('Accion de prueba')

        self.assertEqual(segments, [{'text': 'Accion de prueba', 'style': 'normal'}])

    def test_parse_habilidad_uses_manual_bold_and_parentheses_italics(self):
        segments = srv_textos_views._parse_habilidad('Texto **Accion** (rapida)')

        self.assertEqual(
            segments,
            [
                {'text': 'Texto ', 'style': 'normal'},
                {'text': 'Accion', 'style': 'bold'},
                {'text': ' ', 'style': 'normal'},
                {'text': '(rapida)', 'style': 'italic'},
            ],
        )

    def test_parse_habilidad_keeps_parentheses_italic_inside_explicit_bold(self):
        segments = srv_textos_views._parse_habilidad('**Accion (sigilo)** final')

        self.assertEqual(
            segments,
            [
                {'text': 'Accion ', 'style': 'bold'},
                {'text': '(sigilo)', 'style': 'italic'},
                {'text': ' final', 'style': 'normal'},
            ],
        )

    def test_append_text_tokens_with_inline_symbols_emits_newline_tokens(self):
        _, font_normal = srv_textos_views._load_hab_fonts(28)
        tokens = []

        srv_textos_views._append_text_tokens_with_inline_symbols(
            tokens,
            ' \nSuccessful referendum',
            font_normal,
            'normal',
            28,
        )

        self.assertTrue(any(token.get('type') == 'newline' for token in tokens))
        self.assertTrue(any(token.get('text') == 'Successful' for token in tokens if token.get('type') == 'text'))
        self.assertFalse(any('\n' in token.get('text', '') for token in tokens if token.get('type') == 'text'))

    def test_render_habilidad_does_not_draw_embedded_newlines_inside_words(self):
        image = Image.new('RGBA', (520, 520), (0, 0, 0, 0))

        with patch('apps.srv_textos.views.ImageDraw.ImageDraw.text', autospec=True) as mock_draw_text:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='**Only one Ancient Influence can be played or called in a game.** \n'
                     'Successful referendum means each Methuselah can choose a ready vampire they control.',
                x=80,
                y=100,
                max_width=300,
                font_size=28,
                color='white',
                bg_opacity=0,
                bg_padding=10,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=180,
            )

        drawn_texts = [call.args[2] for call in mock_draw_text.call_args_list]
        self.assertIn('Successful', drawn_texts)
        self.assertFalse(any('\n' in text for text in drawn_texts))

    def test_discipline_ref_to_code_supports_inline_code_case_semantics(self):
        self.assertEqual(srv_textos_views._discipline_ref_to_code('dom'), ('dom', False))
        self.assertEqual(srv_textos_views._discipline_ref_to_code('DOM'), ('dom', True))
        self.assertEqual(srv_textos_views._discipline_ref_to_code('superior Dominate'), ('dom', True))

    def test_segment_to_tokens_libreria_resolves_inline_discipline_symbols(self):
        tokens = srv_textos_views._segment_to_tokens_libreria(
            [{'text': 'Gana [dom] y [DOM].', 'style': 'normal'}],
            font_size=26,
        )

        symbol_paths = [token['path'] for token in tokens if token.get('type') == 'symbol']

        self.assertEqual(len(symbol_paths), 2)
        self.assertTrue(any(path.endswith('static/disc_inf/dom.png') for path in symbol_paths))
        self.assertTrue(any(path.endswith('static/disc_sup/dom.png') for path in symbol_paths))

    def test_segment_to_tokens_libreria_keeps_unknown_markers_as_text(self):
        tokens = srv_textos_views._segment_to_tokens_libreria(
            [{'text': 'Texto [xyz] raro', 'style': 'normal'}],
            font_size=26,
        )

        text_parts = [token['text'] for token in tokens if token.get('type') == 'text']

        self.assertIn('[xyz]', text_parts)
        self.assertFalse(any(token.get('type') == 'symbol' for token in tokens))

    def test_render_habilidad_cripta_loads_inline_inferior_and_superior_discipline_symbols(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))
        fake_symbol = Image.new('RGBA', (24, 24), (255, 255, 255, 255))

        with patch('apps.srv_textos.views._load_symbol', return_value=fake_symbol) as mock_load_symbol:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='Accion: gana [dom] y [DOM].',
                x=100,
                y=120,
                max_width=220,
                font_size=28,
                color='white',
                bg_opacity=0,
                bg_padding=12,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=140,
            )

        symbol_paths = [call.args[0] for call in mock_load_symbol.call_args_list]
        self.assertTrue(any(path.endswith('static/disc_inf/dom.png') for path in symbol_paths))
        self.assertTrue(any(path.endswith('static/disc_sup/dom.png') for path in symbol_paths))

    def test_render_habilidad_libreria_loads_inline_inferior_and_superior_discipline_symbols(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))
        fake_symbol = Image.new('RGBA', (24, 24), (255, 255, 255, 255))

        with patch('apps.srv_textos.views._load_symbol', return_value=fake_symbol) as mock_load_symbol:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='**Accion** [dom] y [DOM]',
                x=90,
                y=110,
                max_width=220,
                font_size=26,
                color='white',
                bg_opacity=0,
                bg_padding=10,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=130,
            )

        symbol_paths = [call.args[0] for call in mock_load_symbol.call_args_list]
        self.assertTrue(any(path.endswith('static/disc_inf/dom.png') for path in symbol_paths))
        self.assertTrue(any(path.endswith('static/disc_sup/dom.png') for path in symbol_paths))

    def test_render_habilidad_reserves_leading_column_for_discipline_prefixed_line(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))
        fake_symbol = Image.new('RGBA', (24, 24), (255, 255, 255, 255))
        words = srv_textos_views._build_habilidad_word_tokens('[aus] +1 intercept.', 28)
        leading_symbol = words[0]
        content_x = 80 + 10
        expected_max_text_x = content_x + leading_symbol['size'] + leading_symbol['gap'] + 12

        with patch('apps.srv_textos.views._load_symbol', return_value=fake_symbol), patch(
            'apps.srv_textos.views.ImageDraw.ImageDraw.text', autospec=True
        ) as mock_draw_text:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='[aus] +1 intercept.',
                x=80,
                y=100,
                max_width=260,
                font_size=28,
                color='white',
                bg_opacity=0,
                bg_padding=10,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=100,
            )

        first_text_position = mock_draw_text.call_args_list[0].args[1]
        self.assertLessEqual(first_text_position[0], expected_max_text_x)

    def test_render_habilidad_keeps_regular_line_out_of_leading_discipline_column(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))
        content_x = 80 + 10

        with patch('apps.srv_textos.views.ImageDraw.ImageDraw.text', autospec=True) as mock_draw_text:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='Requires an Anarch.',
                x=80,
                y=100,
                max_width=260,
                font_size=28,
                color='white',
                bg_opacity=0,
                bg_padding=10,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=100,
            )

        first_text_position = mock_draw_text.call_args_list[0].args[1]
        self.assertLess(first_text_position[0], content_x + 20)

    def test_render_habilidad_wraps_discipline_line_with_hanging_indent(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))
        fake_symbol = Image.new('RGBA', (24, 24), (255, 255, 255, 255))

        with patch('apps.srv_textos.views._load_symbol', return_value=fake_symbol), patch(
            'apps.srv_textos.views.ImageDraw.ImageDraw.text', autospec=True
        ) as mock_draw_text:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='[aus] +1 intercept, even if intercept is not yet needed.',
                x=80,
                y=100,
                max_width=260,
                font_size=28,
                color='white',
                bg_opacity=0,
                bg_padding=10,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=160,
            )

        first_line_x = mock_draw_text.call_args_list[0].args[1][0]
        second_line_x = mock_draw_text.call_args_list[2].args[1][0]
        self.assertLessEqual(abs(first_line_x - second_line_x), 5)

    def test_render_habilidad_uses_box_origin_as_outer_top_left(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))

        srv_textos_views._render_habilidad_text(
            image=image,
            text='Texto de prueba',
            x=100,
            y=120,
            max_width=180,
            font_size=28,
            color='white',
            bg_opacity=255,
            bg_padding=12,
            bg_radius=0,
            line_spacing=3,
            bg_color=(0, 0, 0),
            box_height=140,
        )

        bounds = image.getchannel('A').getbbox()
        self.assertEqual(bounds[0], 100)
        self.assertEqual(bounds[1], 120)

    def test_render_habilidad_libreria_uses_box_origin_as_outer_top_left(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))

        srv_textos_views._render_habilidad_text(
            image=image,
            text='**Accion** de prueba',
            x=90,
            y=110,
            max_width=190,
            font_size=26,
            color='white',
            bg_opacity=255,
            bg_padding=10,
            bg_radius=0,
            line_spacing=3,
            bg_color=(0, 0, 0),
            box_height=130,
            use_visual_content_height=True,
        )

        bounds = image.getchannel('A').getbbox()
        self.assertEqual(bounds[0], 90)
        self.assertEqual(bounds[1], 110)

    def test_render_habilidad_centers_text_vertically_inside_box(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))

        srv_textos_views._render_habilidad_text(
            image=image,
            text='Texto de prueba',
            x=100,
            y=120,
            max_width=180,
            font_size=28,
            color='white',
            bg_opacity=0,
            bg_padding=12,
            bg_radius=0,
            line_spacing=3,
            bg_color=(0, 0, 0),
            box_height=140,
        )

        bounds = image.getchannel('A').getbbox()
        top_gap = bounds[1] - 120
        bottom_gap = (120 + 140) - bounds[3]

        self.assertLessEqual(abs(top_gap - bottom_gap), 20)

    def test_render_habilidad_libreria_centers_text_vertically_inside_box(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))

        srv_textos_views._render_habilidad_text(
            image=image,
            text='**Accion** de prueba',
            x=90,
            y=110,
            max_width=190,
            font_size=26,
            color='white',
            bg_opacity=0,
            bg_padding=10,
            bg_radius=0,
            line_spacing=3,
            bg_color=(0, 0, 0),
            box_height=130,
        )

        bounds = image.getchannel('A').getbbox()
        top_gap = bounds[1] - 110
        bottom_gap = (110 + 130) - bounds[3]

        self.assertLessEqual(abs(top_gap - bottom_gap), 20)

    def test_render_habilidad_libreria_visible_gaps_follow_configured_vertical_margin(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['box'] = {
            'x': 54,
            'y': 971,
            'width': 639,
            'height': 17,
        }
        config['habilidad']['bg_padding'] = 19
        text = (
            '**Only one Ancient Influence can be played or called in a game.**\n'
            'Successful referendum means each Methuselah can choose a ready vampire they control. '
            "Each Methuselah gains pool equal to their chosen vampire's capacity, then burns 5 pool."
        )

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            text,
            hab_font_size=32,
        )
        hab_box = metrics['habilidad']['used_box']
        image = Image.new('RGBA', (745, 1040), (0, 0, 0, 0))

        srv_textos_views._render_habilidad_text(
            image=image,
            text=text,
            x=hab_box['x'],
            y=hab_box['y'],
            max_width=hab_box['width'],
            font_size=32,
            color='white',
            bg_opacity=0,
            bg_padding=config['habilidad']['bg_padding'],
            vertical_padding=metrics['habilidad']['vertical_padding'],
            bg_radius=0,
            line_spacing=config['habilidad']['line_spacing'],
            bg_color=(0, 0, 0),
            box_height=hab_box['height'],
            use_visual_content_height=True,
        )

        bounds = image.getchannel('A').getbbox()
        top_gap = bounds[1] - hab_box['y']
        bottom_gap = (hab_box['y'] + hab_box['height']) - bounds[3]

        self.assertLessEqual(top_gap, 25)
        self.assertLessEqual(bottom_gap, 25)
        self.assertLessEqual(abs(top_gap - bottom_gap), 8)

    def test_render_habilidad_can_use_vertical_padding_independent_from_bg_padding(self):
        image = Image.new('RGBA', (420, 420), (0, 0, 0, 0))

        with patch('PIL.ImageDraw.ImageDraw.text', autospec=True) as mock_text:
            srv_textos_views._render_habilidad_text(
                image=image,
                text='Texto de prueba',
                x=90,
                y=110,
                max_width=190,
                font_size=26,
                color='white',
                bg_opacity=0,
                bg_padding=19,
                vertical_padding=4,
                bg_radius=0,
                line_spacing=3,
                bg_color=(0, 0, 0),
                box_height=37,
            )

        draw_position = mock_text.call_args_list[0].args[1]
        self.assertEqual(draw_position[1], 114)


class NameIllustratorBoxRenderTests(TestCase):
    def test_nombre_uses_box_alignment_and_shadow_toggle(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['rules']['align'] = 'right'
        config['nombre']['shadow']['enabled'] = False

        metrics = srv_textos_views._compute_layout_metrics(config, card_type='cripta', habilidad='')

        self.assertEqual(metrics['nombre']['align'], 'right')
        self.assertFalse(metrics['nombre']['shadow_enabled'])

    def test_ilustrador_stays_within_box(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))

        metrics = srv_textos_views._compute_layout_metrics(config, card_type='cripta', habilidad='x')

        self.assertLessEqual(
            metrics['ilustrador']['text_width'],
            metrics['ilustrador']['box']['width'],
        )

    def test_ilustrador_metrics_use_classic_style_in_cripta(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['ilustrador']['font_size'] = 60
        config['ilustrador']['color'] = 'red'
        config['ilustrador']['box']['width'] = 500

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            card_type='cripta',
            habilidad='',
            ilustrador='Crafted with AI',
        )

        self.assertEqual(metrics['ilustrador']['style']['font_size'], 24)
        self.assertEqual(metrics['ilustrador']['style']['color'], 'white')
        self.assertEqual(metrics['ilustrador']['fit']['font_size'], 24)

    def test_ilustrador_metrics_use_classic_style_in_libreria(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['ilustrador']['font_size'] = 60
        config['ilustrador']['color'] = 'red'
        config['ilustrador']['box']['width'] = 500

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            card_type='libreria',
            habilidad='',
            ilustrador='Crafted with AI',
        )

        self.assertEqual(metrics['ilustrador']['style']['font_size'], 24)
        self.assertEqual(metrics['ilustrador']['style']['color'], 'white')
        self.assertEqual(metrics['ilustrador']['fit']['font_size'], 24)


class SymbolsDiscBoxSizingTests(SimpleTestCase):
    def test_disciplines_size_scales_from_box_width(self):
        box = {'x': 10, 'y': 100, 'width': 120, 'height': 280}
        size, spacing = srv_textos_views._compute_disc_metrics_from_box(box, icon_count=3)

        self.assertLessEqual(size, 120)
        self.assertGreater(spacing, 0)

    def test_symbols_do_not_overflow_box(self):
        box = {'x': 10, 'y': 100, 'width': 100, 'height': 300}
        metrics = srv_textos_views._compute_symbol_metrics_from_box(box, icon_count=4)

        self.assertLessEqual(metrics['size'], 100)

    def test_libreria_metrics_keep_root_level_simbolos_section(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            card_type='libreria',
            simbolos=['action', 'equipment'],
        )

        self.assertIn('simbolos', metrics)
        self.assertEqual(metrics['simbolos']['box']['x'], config['simbolos']['box']['x'])
        self.assertEqual(metrics['simbolos']['box']['y'], config['simbolos']['box']['y'])


class HabilidadDynamicHeightTests(SimpleTestCase):
    def test_cripta_dynamic_habilidad_uses_effective_render_font_size(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {
            'x': 160,
            'y': 700,
            'width': 420,
            'height': 160,
        }

        small_font_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto de habilidad suficientemente largo para ocupar varias lineas',
            dynamic_habilidad_from_bottom=True,
            hab_font_size=20,
        )
        large_font_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto de habilidad suficientemente largo para ocupar varias lineas',
            dynamic_habilidad_from_bottom=True,
            hab_font_size=50,
        )

        self.assertGreater(
            large_font_metrics['habilidad']['used_box']['height'],
            small_font_metrics['habilidad']['used_box']['height'],
        )

    def test_habilidad_box_without_flag_remains_fixed(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {
            'x': 140,
            'y': 760,
            'width': 420,
            'height': 160,
        }

        short_metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'corto')
        long_metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'texto ' * 40)

        self.assertEqual(short_metrics['habilidad']['box']['height'], 160)
        self.assertEqual(long_metrics['habilidad']['box']['height'], 160)
        self.assertGreater(
            long_metrics['habilidad']['used_box']['height'],
            short_metrics['habilidad']['used_box']['height'],
        )
        self.assertLessEqual(long_metrics['habilidad']['used_box']['height'], 160)
        self.assertEqual(long_metrics['habilidad']['used_box']['y'], 760)

    def test_cripta_dynamic_habilidad_from_bottom_uses_only_bottom_edge(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['x'] = 10
        config['habilidad']['y_ratio'] = 0.1
        config['habilidad']['max_width_ratio'] = 0.2
        config['habilidad']['box_bottom_ratio'] = 0.3
        config['habilidad']['box'] = {
            'x': 222,
            'y': 333,
            'width': 444,
            'height': 120,
        }

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'texto ' * 30,
            dynamic_habilidad_from_bottom=True,
        )

        self.assertEqual(metrics['habilidad']['box']['x'], 222)
        self.assertEqual(metrics['habilidad']['box']['y'], 333)
        self.assertEqual(metrics['habilidad']['box']['width'], 444)
        self.assertEqual(metrics['habilidad']['box']['height'], 120)
        self.assertEqual(
            metrics['habilidad']['used_box']['y'] + metrics['habilidad']['used_box']['height'],
            453,
        )
        self.assertLess(metrics['habilidad']['used_box']['y'], 333)

    def test_habilidad_prefers_explicit_box_coordinates_without_growing_layout_box(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['x'] = 10
        config['habilidad']['y_ratio'] = 0.1
        config['habilidad']['max_width_ratio'] = 0.2
        config['habilidad']['box_bottom_ratio'] = 0.3
        config['habilidad']['box'] = {
            'x': 222,
            'y': 333,
            'width': 444,
            'height': 120,
        }

        metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'texto corto')

        self.assertEqual(metrics['habilidad']['box']['x'], 222)
        self.assertEqual(metrics['habilidad']['box']['y'], 333)
        self.assertEqual(metrics['habilidad']['box']['width'], 444)
        self.assertEqual(metrics['habilidad']['box']['height'], 120)
        self.assertLessEqual(metrics['habilidad']['used_box']['height'], 120)
        self.assertGreaterEqual(metrics['habilidad']['used_box']['y'], 333)

    def test_habilidad_used_box_is_clamped_to_card_top_when_flag_is_enabled(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {
            'x': 140,
            'y': 300,
            'width': 420,
            'height': 100,
        }

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'texto ' * 120,
            dynamic_habilidad_from_bottom=True,
        )

        self.assertEqual(metrics['habilidad']['used_box']['y'], 0)
        self.assertEqual(metrics['habilidad']['used_box']['height'], 400)
        self.assertEqual(
            metrics['habilidad']['used_box']['y'] + metrics['habilidad']['used_box']['height'],
            400,
        )

    def test_libreria_habilidad_bottom_anchor_margin_grows_up_from_bottom(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['box'] = {
            'x': 170,
            'y': 820,
            'width': 420,
            'height': 24,
        }

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto de prueba suficientemente largo para ocupar varias lineas dentro del cuadro de habilidad.',
        )

        self.assertEqual(metrics['habilidad']['box']['y'], 820)
        self.assertEqual(
            metrics['habilidad']['used_box']['y'] + metrics['habilidad']['used_box']['height'],
            820,
        )
        self.assertLess(metrics['habilidad']['used_box']['y'], 820)

    def test_libreria_habilidad_bottom_anchor_margin_uses_symmetric_vertical_margin(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['font_size'] = 32
        config['habilidad']['line_spacing'] = 4
        config['habilidad']['bg_padding'] = 19
        config['habilidad']['box'] = {
            'x': 170,
            'y': 820,
            'width': 420,
            'height': 26,
        }
        habilidad = 'Texto de prueba de varias lineas para medir el margen superior e inferior del recuadro.'

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            habilidad,
        )

        content_height = srv_textos_views._compute_habilidad_visual_content_height(
            habilidad=habilidad,
            font_size=32,
            max_width=420,
            line_spacing=4,
            horizontal_padding=19,
        )

        self.assertEqual(metrics['habilidad']['used_box']['height'], content_height + (26 * 2))

    def test_libreria_habilidad_bottom_anchor_margin_uses_box_height_as_only_vertical_margin(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['font_size'] = 32
        config['habilidad']['line_spacing'] = 4
        config['habilidad']['bg_padding'] = 19
        config['habilidad']['box'] = {
            'x': 170,
            'y': 820,
            'width': 420,
            'height': 4,
        }
        habilidad = 'Texto de prueba de varias lineas para medir que el aire vertical dependa solo de box.height.'

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            habilidad,
        )

        content_height = srv_textos_views._compute_habilidad_visual_content_height(
            habilidad=habilidad,
            font_size=32,
            max_width=420,
            line_spacing=4,
            horizontal_padding=19,
        )

        self.assertEqual(metrics['habilidad']['used_box']['height'], content_height + (4 * 2))

    def test_libreria_habilidad_bottom_anchor_margin_grows_with_effective_font_size(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'bottom_anchor_margin'
        config['habilidad']['box'] = {
            'x': 170,
            'y': 820,
            'width': 420,
            'height': 24,
        }
        habilidad = 'Texto de habilidad suficientemente largo para notar el crecimiento del recuadro.'

        small_font_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            habilidad,
            hab_font_size=20,
        )
        large_font_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            habilidad,
            hab_font_size=48,
        )

        self.assertGreater(
            large_font_metrics['habilidad']['used_box']['height'],
            small_font_metrics['habilidad']['used_box']['height'],
        )
        self.assertEqual(
            small_font_metrics['habilidad']['used_box']['y'] + small_font_metrics['habilidad']['used_box']['height'],
            820,
        )
        self.assertEqual(
            large_font_metrics['habilidad']['used_box']['y'] + large_font_metrics['habilidad']['used_box']['height'],
            820,
        )

    def test_libreria_habilidad_legacy_semantics_is_responsive_from_legacy_bottom_edge(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'legacy'
        config['habilidad']['box'] = {
            'x': 54,
            'y': 678,
            'width': 639,
            'height': 290,
        }

        short_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            hab_font_size=24,
        )
        long_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'texto ' * 80,
            hab_font_size=24,
        )

        legacy_bottom_edge = 968

        self.assertEqual(
            short_metrics['habilidad']['used_box']['y'] + short_metrics['habilidad']['used_box']['height'],
            legacy_bottom_edge,
        )
        self.assertEqual(
            long_metrics['habilidad']['used_box']['y'] + long_metrics['habilidad']['used_box']['height'],
            legacy_bottom_edge,
        )
        self.assertGreater(
            long_metrics['habilidad']['used_box']['height'],
            short_metrics['habilidad']['used_box']['height'],
        )
        self.assertLess(
            short_metrics['habilidad']['used_box']['height'],
            config['habilidad']['box']['height'],
        )

    def test_libreria_habilidad_missing_box_semantics_is_responsive_from_legacy_bottom_edge(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        del config['habilidad']['rules']['box_semantics']
        config['habilidad']['box'] = {
            'x': 54,
            'y': 678,
            'width': 639,
            'height': 290,
        }

        short_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            hab_font_size=24,
        )
        long_metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'texto ' * 80,
            hab_font_size=24,
        )

        legacy_bottom_edge = 968

        self.assertEqual(
            short_metrics['habilidad']['used_box']['y'] + short_metrics['habilidad']['used_box']['height'],
            legacy_bottom_edge,
        )
        self.assertEqual(
            long_metrics['habilidad']['used_box']['y'] + long_metrics['habilidad']['used_box']['height'],
            legacy_bottom_edge,
        )
        self.assertGreater(
            long_metrics['habilidad']['used_box']['height'],
            short_metrics['habilidad']['used_box']['height'],
        )
        self.assertLess(
            short_metrics['habilidad']['used_box']['height'],
            config['habilidad']['box']['height'],
        )

    def test_libreria_disciplinas_follow_migrated_legacy_habilidad_box(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['rules']['box_semantics'] = 'legacy'
        config['habilidad']['box'] = {
            'x': 54,
            'y': 678,
            'width': 639,
            'height': 290,
        }
        config['disciplinas']['box'] = {
            'x': 54,
            'y': 721,
            'width': 85,
            'height': 91,
        }
        config['disciplinas']['rules'] = {'anchor_mode': 'free', 'gap_from_habilidad': 31}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            disciplinas=[{'name': 'dom', 'level': 'inf'}, {'name': 'tha', 'level': 'inf'}],
        )

        self.assertGreater(metrics['disciplinas']['box']['y'], 0)
        self.assertEqual(metrics['disciplinas']['box']['y'], metrics['habilidad']['used_box']['y'] - 31)

    def test_disciplinas_vertical_anchor_uses_habilidad_gap_when_free(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {
            'x': 140,
            'y': 780,
            'width': 420,
            'height': 140,
        }
        config['disciplinas']['box'] = {
            'x': 30,
            'y': 10,
            'width': 64,
            'height': 180,
        }
        config['disciplinas']['rules'] = {'anchor_mode': 'free', 'gap_from_habilidad': 0}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[{'name': 'ani', 'level': 'inf'}, {'name': 'for', 'level': 'inf'}, {'name': 'pot', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['x'], 30)
        self.assertEqual(metrics['disciplinas']['box']['width'], 64)
        self.assertEqual(metrics['disciplinas']['box']['y'], metrics['habilidad']['used_box']['y'])

    def test_disciplinas_free_mode_uses_fixed_gap_from_habilidad(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {'x': 140, 'y': 780, 'width': 420, 'height': 140}
        config['disciplinas']['box'] = {'x': 18, 'y': 90, 'width': 72, 'height': 82}
        config['disciplinas']['rules'] = {'anchor_mode': 'free', 'gap_from_habilidad': 24}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[{'name': 'ani', 'level': 'inf'}, {'name': 'for', 'level': 'inf'}, {'name': 'pot', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['y'], metrics['habilidad']['used_box']['y'] - 24)

    def test_disciplinas_size_depends_on_box_width_and_spacing_on_box_height(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['disciplinas']['box'] = {
            'x': 18,
            'y': 90,
            'width': 72,
            'height': 210,
        }

        metrics_two = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[{'name': 'ani', 'level': 'inf'}, {'name': 'for', 'level': 'inf'}],
        )
        metrics_six = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[
                {'name': 'ani', 'level': 'inf'},
                {'name': 'for', 'level': 'inf'},
                {'name': 'pot', 'level': 'inf'},
                {'name': 'aus', 'level': 'inf'},
                {'name': 'cel', 'level': 'inf'},
                {'name': 'dom', 'level': 'inf'},
            ],
        )

        self.assertEqual(metrics_two['disciplinas']['size'], 72)
        self.assertEqual(metrics_two['disciplinas']['spacing'], 210)
        self.assertEqual(metrics_six['disciplinas']['size'], 72)
        self.assertEqual(metrics_six['disciplinas']['spacing'], 210)

    def test_disciplinas_fixed_bottom_preserves_configured_bottom_edge(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {
            'x': 140,
            'y': 780,
            'width': 420,
            'height': 140,
        }
        config['disciplinas']['box'] = {
            'x': 24,
            'y': 620,
            'width': 70,
            'height': 82,
        }
        config['disciplinas']['rules'] = {'anchor_mode': 'fixed_bottom', 'gap_from_habilidad': 0}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[{'name': 'ani', 'level': 'inf'}, {'name': 'for', 'level': 'inf'}, {'name': 'pot', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['y'], 620)

    def test_libreria_disciplinas_vertical_anchor_uses_habilidad_gap_when_free(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['box'] = {
            'x': 170,
            'y': 720,
            'width': 420,
            'height': 180,
        }
        config['disciplinas']['box'] = {
            'x': 30,
            'y': 10,
            'width': 64,
            'height': 180,
        }
        config['disciplinas']['rules'] = {'anchor_mode': 'free', 'gap_from_habilidad': 0}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            disciplinas=[{'name': 'dom', 'level': 'inf'}, {'name': 'nec', 'level': 'inf'}, {'name': 'tha', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['x'], 30)
        self.assertEqual(metrics['disciplinas']['box']['width'], 64)
        self.assertEqual(metrics['disciplinas']['box']['y'], metrics['habilidad']['used_box']['y'])

    def test_libreria_disciplinas_free_mode_uses_fixed_gap_from_habilidad(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['box'] = {'x': 170, 'y': 720, 'width': 420, 'height': 180}
        config['disciplinas']['box'] = {'x': 18, 'y': 90, 'width': 72, 'height': 82}
        config['disciplinas']['rules'] = {'anchor_mode': 'free', 'gap_from_habilidad': 24}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            disciplinas=[{'name': 'dom', 'level': 'inf'}, {'name': 'nec', 'level': 'inf'}, {'name': 'tha', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['y'], metrics['habilidad']['used_box']['y'] - 24)

    def test_libreria_disciplinas_size_depends_on_box_width_and_spacing_on_box_height(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['disciplinas']['box'] = {
            'x': 18,
            'y': 90,
            'width': 72,
            'height': 210,
        }

        metrics_two = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            disciplinas=[{'name': 'dom', 'level': 'inf'}, {'name': 'nec', 'level': 'inf'}],
        )
        metrics_six = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            disciplinas=[
                {'name': 'dom', 'level': 'inf'},
                {'name': 'nec', 'level': 'inf'},
                {'name': 'tha', 'level': 'inf'},
                {'name': 'aus', 'level': 'inf'},
                {'name': 'cel', 'level': 'inf'},
                {'name': 'obf', 'level': 'inf'},
            ],
        )

        self.assertEqual(metrics_two['disciplinas']['size'], 72)
        self.assertEqual(metrics_two['disciplinas']['spacing'], 210)
        self.assertEqual(metrics_six['disciplinas']['size'], 72)
        self.assertEqual(metrics_six['disciplinas']['spacing'], 210)

    def test_libreria_disciplinas_fixed_bottom_preserves_configured_bottom_edge(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['habilidad']['box'] = {
            'x': 170,
            'y': 720,
            'width': 420,
            'height': 180,
        }
        config['disciplinas']['box'] = {
            'x': 24,
            'y': 620,
            'width': 70,
            'height': 82,
        }
        config['disciplinas']['rules'] = {'anchor_mode': 'fixed_bottom', 'gap_from_habilidad': 0}

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'libreria',
            'Texto corto',
            disciplinas=[{'name': 'dom', 'level': 'inf'}, {'name': 'nec', 'level': 'inf'}, {'name': 'tha', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['y'], 620)

    def test_cripta_explicit_box_starts_stack_from_bottom_anchor(self):
        positions = srv_textos_views._compute_vertical_stack_positions(
            box={'x': 10, 'y': 190, 'width': 90, 'height': 90},
            item_size=80,
            spacing=90,
            item_count=2,
            source='box',
        )

        self.assertEqual(positions, [110, 20])


class RenderClanContextTests(TestCase):
    def test_render_clan_propagates_dynamic_habilidad_from_bottom(self):
        payload = {
            'card_type': 'cripta',
            'layout_override': load_classic_seed('cripta'),
            'clan': '',
            'nombre': 'Arika',
            'senda': '',
            'disciplinas': [],
            'simbolos': [],
            'habilidad': 'Texto',
            'coste': '',
            'cripta': '',
            'ilustrador': '',
            'hab_opacity': 180,
            'hab_font_size': 33,
            'imagen_url': '/media/recortes/base.png',
            'dynamic_habilidad_from_bottom': True,
        }

        with patch('apps.srv_textos.views._render_carta', return_value=('/media/render/test.png', None)) as mock_render:
            response = self.client.post(
                '/srv-textos/render-clan/',
                data=json.dumps(payload),
                content_type='application/json',
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['imagen_url'], '/media/render/test.png')
        self.assertTrue(mock_render.call_args.kwargs['dynamic_habilidad_from_bottom'])


class GlobalCollisionResolverTests(SimpleTestCase):
    def test_collision_resolver_moves_elements_up_when_habilidad_grows(self):
        metrics = {
            'habilidad': {'box': {'x': 150, 'y': 600, 'width': 400, 'height': 300}},
            'disciplinas': {'box': {'x': 40, 'y': 680, 'width': 90, 'height': 260}, 'anchor_mode': 'free'},
        }

        resolved = srv_textos_views._resolve_global_collisions(metrics, card_height=1040)

        self.assertLess(resolved['disciplinas']['box']['y'], 680)

    def test_collision_resolver_keeps_explicit_free_boxes_in_place(self):
        metrics = {
            'habilidad': {'box': {'x': 150, 'y': 600, 'width': 400, 'height': 300}, 'source': 'box'},
            'disciplinas': {
                'box': {'x': 40, 'y': 680, 'width': 90, 'height': 260},
                'anchor_mode': 'free',
                'source': 'box',
            },
            'ilustrador': {
                'box': {'x': 160, 'y': 760, 'width': 260, 'height': 40},
                'anchor_mode': 'free',
                'source': 'box',
            },
        }

        resolved = srv_textos_views._resolve_global_collisions(metrics, card_height=1040)

        self.assertEqual(resolved['disciplinas']['box']['y'], 680)
        self.assertEqual(resolved['ilustrador']['box']['y'], 760)

    def test_collision_resolver_keeps_fixed_bottom_boxes_in_place(self):
        metrics = {
            'habilidad': {'box': {'x': 150, 'y': 600, 'width': 400, 'height': 300}, 'source': 'box'},
            'disciplinas': {
                'box': {'x': 40, 'y': 680, 'width': 90, 'height': 260},
                'anchor_mode': 'fixed_bottom',
                'source': 'box',
            },
        }

        resolved = srv_textos_views._resolve_global_collisions(metrics, card_height=1040)

        self.assertEqual(resolved['disciplinas']['box']['y'], 680)


class CriptaBoxMetricsTests(SimpleTestCase):
    def test_metrics_include_explicit_cripta_box(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['habilidad']['box'] = {
            'x': 210,
            'y': 640,
            'width': 330,
            'height': 180,
        }
        config['cripta']['box'] = {
            'x': 70,
            'y': 560,
            'width': 90,
            'height': 40,
        }

        metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'texto corto')

        self.assertEqual(metrics['cripta']['box']['x'], 70)
        self.assertEqual(metrics['cripta']['box']['y'], 560)

    def test_metrics_use_classic_style_for_cripta_number(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['cripta']['font_size'] = 80
        config['cripta']['color'] = 'red'

        metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'texto corto')

        self.assertEqual(metrics['cripta']['style']['font_size'], 35)
        self.assertEqual(metrics['cripta']['style']['color'], 'white')


class VerticalStackPositionTests(SimpleTestCase):
    def test_explicit_box_starts_stack_from_bottom_anchor(self):
        positions = srv_textos_views._compute_vertical_stack_positions(
            box={'x': 10, 'y': 100, 'width': 90, 'height': 260},
            item_size=80,
            spacing=90,
            item_count=2,
            source='box',
        )

        self.assertEqual(positions, [20])


class BoxEngineRenderRegressionTests(TestCase):
    def test_render_texto_accepts_v2_layout_override(self):
        override = normalize_layout_config('cripta', load_classic_seed('cripta'))
        override['nombre']['rules']['align'] = 'right'

        response = self.client.post(
            '/srv-textos/render-texto/',
            data=json.dumps({
                'card_type': 'cripta',
                'imagen_url': '/media/recortes/test.png',
                'layout_override': override,
                'nombre': 'Carta ejemplo',
            }),
            content_type='application/json',
        )

        self.assertIn(response.status_code, (200, 404))


class RenderFromPathTests(TestCase):
    def test_render_carta_from_absolute_path_prepares_media_source(self):
        image_path = os.path.join(settings.BASE_DIR, 'static', 'layouts', 'images', 'Mimir.png')

        with patch('apps.srv_textos.views._render_carta', return_value=('/media/render/from-path.png', None)) as mock_render:
            render_url, error = srv_textos_views._render_carta_from_path(
                image_path,
                nombre='Mimir',
                clan='',
                senda='',
                disciplinas=[],
                simbolos=[],
                habilidad='',
                coste='',
                cripta='',
                ilustrador='Crafted with AI',
                card_type='cripta',
                layout_config=load_classic_seed('cripta'),
            )

        self.assertIsNone(error)
        self.assertEqual(render_url, '/media/render/from-path.png')
        prepared_url = mock_render.call_args.kwargs['imagen_url']
        self.assertTrue(prepared_url.startswith('/media/layout_preview_sources/'))
        prepared_path = os.path.join(settings.MEDIA_ROOT, prepared_url.replace(settings.MEDIA_URL, ''))
        self.assertTrue(os.path.exists(prepared_path))


class ClassicStyleRenderTests(TestCase):
    def _make_temp_image_path(self):
        temp_dir = tempfile.TemporaryDirectory()
        image_path = os.path.join(temp_dir.name, 'base.png')
        Image.new('RGBA', (745, 1040), (0, 0, 0, 0)).save(image_path)
        self.addCleanup(temp_dir.cleanup)
        return image_path

    def test_render_cripta_uses_classic_style_even_if_layout_overrides_it(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['cripta']['font_size'] = 80
        config['cripta']['color'] = 'red'
        image_path = self._make_temp_image_path()

        with patch('apps.srv_textos.views.ImageDraw.ImageDraw.text') as mock_text:
            render_url, error = srv_textos_views._render_carta_from_path(
                image_path,
                nombre='',
                clan='',
                senda='',
                disciplinas=[],
                simbolos=[],
                habilidad='',
                coste='',
                cripta='5',
                ilustrador='',
                card_type='cripta',
                layout_config=config,
            )

        self.assertIsNone(error)
        self.assertTrue(render_url.startswith('/media/render/'))
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args.kwargs['fill'], 'white')
        self.assertEqual(mock_text.call_args.kwargs['font'].size, 35)

    def test_render_ilustrador_uses_classic_style_even_if_layout_overrides_it(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['ilustrador']['font_size'] = 60
        config['ilustrador']['color'] = 'red'
        image_path = self._make_temp_image_path()

        with patch('apps.srv_textos.views.ImageDraw.ImageDraw.text') as mock_text:
            render_url, error = srv_textos_views._render_carta_from_path(
                image_path,
                nombre='',
                clan='',
                senda='',
                disciplinas=[],
                simbolos=[],
                habilidad='',
                coste='',
                cripta='',
                ilustrador='Crafted with AI',
                card_type='cripta',
                layout_config=config,
            )

        self.assertIsNone(error)
        self.assertTrue(render_url.startswith('/media/render/'))
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args.kwargs['fill'], 'white')
        self.assertEqual(mock_text.call_args.kwargs['font'].size, 24)

    def test_render_libreria_ilustrador_uses_classic_style_even_if_layout_overrides_it(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        config['ilustrador']['font_size'] = 60
        config['ilustrador']['color'] = 'red'
        image_path = self._make_temp_image_path()

        with patch('apps.srv_textos.views.ImageDraw.ImageDraw.text') as mock_text:
            render_url, error = srv_textos_views._render_carta_from_path(
                image_path,
                nombre='',
                clan='',
                senda='',
                disciplinas=[],
                simbolos=[],
                habilidad='',
                coste='',
                cripta='',
                ilustrador='Crafted with AI',
                card_type='libreria',
                layout_config=config,
            )

        self.assertIsNone(error)
        self.assertTrue(render_url.startswith('/media/render/'))
        self.assertEqual(mock_text.call_count, 1)
        self.assertEqual(mock_text.call_args.kwargs['fill'], 'white')
        self.assertEqual(mock_text.call_args.kwargs['font'].size, 24)

    def test_render_libreria_composites_selected_symbols(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        image_path = self._make_temp_image_path()

        with patch('apps.srv_textos.views._load_symbol', return_value=Image.new('RGBA', (32, 32), (255, 0, 0, 255))):
            with patch('PIL.Image.Image.alpha_composite') as mock_alpha:
                render_url, error = srv_textos_views._render_carta_from_path(
                    image_path,
                    nombre='',
                    clan='',
                    senda='',
                    disciplinas=[],
                    simbolos=['action', 'equipment'],
                    habilidad='',
                    coste='',
                    cripta='',
                    ilustrador='',
                    card_type='libreria',
                    layout_config=config,
                )

        self.assertIsNone(error)
        self.assertTrue(render_url.startswith('/media/render/'))
        self.assertGreaterEqual(mock_alpha.call_count, 2)

    def test_render_libreria_composites_selected_senda(self):
        config = normalize_layout_config('libreria', load_classic_seed('libreria'))
        image_path = self._make_temp_image_path()

        with patch('apps.srv_textos.views._load_symbol', return_value=Image.new('RGBA', (32, 32), (255, 0, 0, 255))):
            with patch('PIL.Image.Image.alpha_composite') as mock_alpha:
                render_url, error = srv_textos_views._render_carta_from_path(
                    image_path,
                    nombre='',
                    clan='',
                    senda='death.png',
                    disciplinas=[],
                    simbolos=[],
                    habilidad='',
                    coste='',
                    cripta='',
                    ilustrador='',
                    card_type='libreria',
                    layout_config=config,
                )

        self.assertIsNone(error)
        self.assertTrue(render_url.startswith('/media/render/'))
        self.assertGreaterEqual(mock_alpha.call_count, 1)
