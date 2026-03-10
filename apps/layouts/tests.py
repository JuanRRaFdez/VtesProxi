from copy import deepcopy
import json

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.layouts.models import UserLayout
from apps.layouts.services import load_classic_seed


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
