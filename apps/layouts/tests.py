from copy import deepcopy
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.layouts.models import UserLayout
from apps.layouts.services import (
    LayoutValidationError,
    load_classic_seed,
    normalize_layout_config,
    validate_layout_config,
)


class UserLayoutModelTests(TestCase):
    def test_unique_name_per_user_and_card_type(self):
        user = get_user_model().objects.create_user(username='alice', password='secret')
        UserLayout.objects.create(
            user=user,
            name='Mi layout',
            card_type='cripta',
            config={},
            is_default=False,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserLayout.objects.create(
                    user=user,
                    name='Mi layout',
                    card_type='cripta',
                    config={},
                    is_default=False,
                )

    def test_only_one_default_per_user_and_card_type(self):
        user = get_user_model().objects.create_user(username='bob', password='secret')
        UserLayout.objects.create(
            user=user,
            name='Default 1',
            card_type='libreria',
            config={},
            is_default=True,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                UserLayout.objects.create(
                    user=user,
                    name='Default 2',
                    card_type='libreria',
                    config={},
                    is_default=True,
                )


class LayoutEditorAccessTests(TestCase):
    def test_editor_requires_login(self):
        response = self.client.get('/layouts/')
        self.assertEqual(response.status_code, 302)


class LayoutApiListCreateTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='editor', password='secret')
        self.other_user = user_model.objects.create_user(username='other', password='secret')

    def test_list_returns_only_current_user_layouts(self):
        own_layout = UserLayout.objects.create(
            user=self.user,
            name='Propio',
            card_type='cripta',
            config={},
            is_default=False,
        )
        UserLayout.objects.create(
            user=self.other_user,
            name='Ajeno',
            card_type='cripta',
            config={},
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.get('/layouts/api/list', {'card_type': 'cripta'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload['layouts']), 1)
        self.assertEqual(payload['layouts'][0]['id'], own_layout.id)

    def test_create_builds_layout_from_classic_seed(self):
        self.client.force_login(self.user)
        response = self.client.post('/layouts/api/create', {
            'name': 'Mi classic',
            'card_type': 'cripta',
        })

        self.assertEqual(response.status_code, 201)
        created = UserLayout.objects.get(user=self.user, name='Mi classic', card_type='cripta')
        self.assertIn('carta', created.config)
        self.assertEqual(created.config['carta']['width'], 745)
        self.assertEqual(created.config['carta']['height'], 1040)

    def test_detail_rejects_other_user_layout(self):
        other_layout = UserLayout.objects.create(
            user=self.other_user,
            name='Privado',
            card_type='cripta',
            config={},
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.get(f'/layouts/api/detail/{other_layout.id}')

        self.assertEqual(response.status_code, 404)


class LayoutConfigValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='config-user', password='secret')
        self.layout = UserLayout.objects.create(
            user=self.user,
            name='Editable',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

    def test_update_config_rejects_invalid_payload(self):
        invalid_config = deepcopy(self.layout.config)
        invalid_config['carta']['width'] = -10

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': invalid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.layout.refresh_from_db()
        self.assertNotEqual(self.layout.config['carta']['width'], -10)

    def test_update_config_accepts_valid_payload(self):
        valid_config = deepcopy(self.layout.config)
        valid_config['carta']['width'] = 900

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': valid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.layout.refresh_from_db()
        self.assertEqual(self.layout.config['carta']['width'], 900)

    def test_update_config_accepts_v2_payload(self):
        valid_config = normalize_layout_config('cripta', deepcopy(self.layout.config))
        valid_config['nombre']['rules']['align'] = 'right'
        valid_config['nombre']['box']['width'] = 320

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({
                'layout_id': self.layout.id,
                'config': valid_config,
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.layout.refresh_from_db()
        self.assertEqual(self.layout.config['nombre']['rules']['align'], 'right')


class LayoutConfigBoxSchemaTests(TestCase):
    def test_normalize_legacy_config_adds_box_for_nombre(self):
        legacy = load_classic_seed('cripta')

        normalized = normalize_layout_config('cripta', legacy)

        self.assertIn('box', normalized['nombre'])
        self.assertEqual(normalized['nombre']['box']['x'], legacy['nombre']['x'])

    def test_normalize_applies_text_defaults_for_nombre_and_ilustrador(self):
        normalized = normalize_layout_config('cripta', load_classic_seed('cripta'))

        self.assertEqual(normalized['nombre']['rules']['align'], 'center')
        self.assertEqual(normalized['ilustrador']['rules']['align'], 'left')


class LayoutConfigValidationV2Tests(TestCase):
    def test_validate_rejects_invalid_align(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['rules']['align'] = 'diagonal'

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)

    def test_validate_rejects_box_out_of_range(self):
        config = normalize_layout_config('cripta', load_classic_seed('cripta'))
        config['nombre']['box']['width'] = -1

        with self.assertRaises(LayoutValidationError):
            validate_layout_config('cripta', config)


class LayoutManagementApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='manage-user', password='secret')
        self.layout = UserLayout.objects.create(
            user=self.user,
            name='Original',
            card_type='cripta',
            config=load_classic_seed('cripta'),
            is_default=False,
        )

    def test_rename_layout(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/rename',
            data=json.dumps({'layout_id': self.layout.id, 'name': 'Renombrado'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.layout.refresh_from_db()
        self.assertEqual(self.layout.name, 'Renombrado')

    def test_delete_layout(self):
        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/delete',
            data=json.dumps({'layout_id': self.layout.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserLayout.objects.filter(id=self.layout.id).exists())

    def test_set_default_switches_previous_default_off(self):
        previous_default = UserLayout.objects.create(
            user=self.user,
            name='Default actual',
            card_type='libreria',
            config=load_classic_seed('libreria'),
            is_default=True,
        )
        next_default = UserLayout.objects.create(
            user=self.user,
            name='Default nuevo',
            card_type='libreria',
            config=load_classic_seed('libreria'),
            is_default=False,
        )

        self.client.force_login(self.user)
        response = self.client.post(
            '/layouts/api/set-default',
            data=json.dumps({'layout_id': next_default.id}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        previous_default.refresh_from_db()
        next_default.refresh_from_db()
        self.assertFalse(previous_default.is_default)
        self.assertTrue(next_default.is_default)


class LayoutEditorTemplateTests(TestCase):
    def test_editor_template_contains_required_mount_points(self):
        user = get_user_model().objects.create_user(username='editor-ui', password='secret')
        self.client.force_login(user)
        response = self.client.get('/layouts/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="layout-stage"')
        self.assertContains(response, 'id="layout-properties"')


class LayoutEditorAdvancedControlsTests(TestCase):
    def test_editor_contains_text_rule_controls(self):
        user = get_user_model().objects.create_user(username='rules-ui', password='secret')
        self.client.force_login(user)

        response = self.client.get('/layouts/')

        self.assertContains(response, 'id="prop-align"')
        self.assertContains(response, 'id="prop-min-font-size"')
        self.assertContains(response, 'id="prop-ellipsis-enabled"')


class EndToEndLayoutFlowTests(TestCase):
    def test_user_can_create_edit_set_default_and_render_with_layout(self):
        user = get_user_model().objects.create_user(username='e2e-user', password='secret')
        self.client.force_login(user)

        create_response = self.client.post(
            '/layouts/api/create',
            data=json.dumps({'name': 'Flujo E2E', 'card_type': 'cripta'}),
            content_type='application/json',
        )
        self.assertEqual(create_response.status_code, 201)
        layout_id = create_response.json()['layout']['id']

        detail_response = self.client.get(f'/layouts/api/detail/{layout_id}')
        self.assertEqual(detail_response.status_code, 200)
        config = detail_response.json()['layout']['config']
        config['carta']['width'] = 910

        update_response = self.client.post(
            '/layouts/api/update-config',
            data=json.dumps({'layout_id': layout_id, 'config': config}),
            content_type='application/json',
        )
        self.assertEqual(update_response.status_code, 200)

        default_response = self.client.post(
            '/layouts/api/set-default',
            data=json.dumps({'layout_id': layout_id}),
            content_type='application/json',
        )
        self.assertEqual(default_response.status_code, 200)

        with patch('apps.srv_textos.views._render_carta', return_value=('/media/render/e2e.png', None)) as mock_render:
            render_response = self.client.post(
                '/srv-textos/render-texto/',
                data=json.dumps({
                    'card_type': 'cripta',
                    'layout_id': layout_id,
                    'layout_name': '',
                    'imagen_url': '/media/recortes/e2e.png',
                    'nombre': 'Carta',
                    'clan': '',
                    'senda': '',
                    'disciplinas': [],
                    'simbolos': [],
                    'habilidad': '',
                    'coste': '',
                    'cripta': '',
                    'ilustrador': '',
                }),
                content_type='application/json',
            )

        self.assertEqual(render_response.status_code, 200)
        self.assertEqual(render_response.json()['imagen_url'], '/media/render/e2e.png')
        self.assertEqual(mock_render.call_count, 1)
        self.assertEqual(mock_render.call_args.kwargs['layout_config']['carta']['width'], 910)
