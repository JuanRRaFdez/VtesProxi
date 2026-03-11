from copy import deepcopy
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

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
    def test_habilidad_height_grows_with_longer_text(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))

        short_metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'corto')
        long_metrics = srv_textos_views._compute_layout_metrics(config, 'cripta', 'texto ' * 40)

        self.assertGreater(long_metrics['habilidad']['height'], short_metrics['habilidad']['height'])


class GlobalCollisionResolverTests(SimpleTestCase):
    def test_collision_resolver_moves_elements_up_when_habilidad_grows(self):
        metrics = {
            'habilidad': {'box': {'x': 150, 'y': 600, 'width': 400, 'height': 300}},
            'disciplinas': {'box': {'x': 40, 'y': 680, 'width': 90, 'height': 260}, 'anchor_mode': 'free'},
        }

        resolved = srv_textos_views._resolve_global_collisions(metrics, card_height=1040)

        self.assertLess(resolved['disciplinas']['box']['y'], 680)


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
