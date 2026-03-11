from copy import deepcopy
import json
import os
import tempfile
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
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
        selected_layout = UserLayout.objects.create(
            user=self.user,
            name='Seleccionado',
            card_type='cripta',
            config=load_classic_seed('cripta'),
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

        UserLayout.objects.create(
            user=self.user,
            name='Default',
            card_type='cripta',
            config=default_layout,
            is_default=True,
        )
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

        self.cripta_default = UserLayout.objects.create(
            user=self.user,
            name='Cripta default',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=True,
        )
        self.cripta_alt = UserLayout.objects.create(
            user=self.user,
            name='Cripta alt',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )
        self.libreria_default = UserLayout.objects.create(
            user=self.user,
            name='Libreria default',
            card_type='libreria',
            config=load_classic_seed('libreria'),
            is_default=True,
        )
        UserLayout.objects.create(
            user=self.other_user,
            name='Ajeno',
            card_type='cripta',
            config=load_classic_seed('cripta'),
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

        srv_textos_views._render_habilidad_text_libreria(
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

        srv_textos_views._render_habilidad_text_libreria(
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

    def test_disciplinas_vertical_anchor_is_derived_from_habilidad_used_box(self):
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

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[{'name': 'ani', 'level': 'inf'}, {'name': 'for', 'level': 'inf'}, {'name': 'pot', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['box']['x'], 30)
        self.assertEqual(metrics['disciplinas']['box']['width'], 64)
        self.assertEqual(
            metrics['disciplinas']['box']['y'] + metrics['disciplinas']['box']['height'],
            metrics['habilidad']['used_box']['y'],
        )

    def test_disciplinas_size_depends_on_box_width_and_spacing_on_box_height(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['disciplinas']['box'] = {
            'x': 18,
            'y': 90,
            'width': 72,
            'height': 210,
        }

        metrics = srv_textos_views._compute_layout_metrics(
            config,
            'cripta',
            'Texto corto',
            disciplinas=[{'name': 'ani', 'level': 'inf'}, {'name': 'for', 'level': 'inf'}, {'name': 'pot', 'level': 'inf'}],
        )

        self.assertEqual(metrics['disciplinas']['size'], 72)
        self.assertEqual(metrics['disciplinas']['spacing'], 70)


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
    def test_explicit_box_starts_stack_from_top(self):
        positions = srv_textos_views._compute_vertical_stack_positions(
            box={'x': 10, 'y': 100, 'width': 90, 'height': 260},
            item_size=80,
            spacing=90,
            item_count=2,
            source='box',
        )

        self.assertEqual(positions, [100, 190])


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
