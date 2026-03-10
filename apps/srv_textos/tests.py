from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase

from apps.layouts.models import UserLayout
from apps.layouts.services import load_classic_seed
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
