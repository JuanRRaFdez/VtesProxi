import importlib
import os
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase


class SecretKeySettingsTests(SimpleTestCase):
    def _reload_settings(self, env):
        with patch.dict(os.environ, env, clear=True):
            import webvtes.settings as settings_module

            settings_module = importlib.reload(settings_module)
            return settings_module, settings_module.resolve_secret_key()

    def test_secret_key_uses_env_value(self):
        settings_module, resolved_secret = self._reload_settings({
            'DJANGO_ENV': 'production',
            'DJANGO_ALLOW_LOCAL_SECRET_FALLBACK': '0',
            'DJANGO_SECRET_KEY': 'test-secret-from-env',
        })

        self.assertEqual(resolved_secret, 'test-secret-from-env')
        self.assertEqual(settings_module.SECRET_KEY, 'test-secret-from-env')

    def test_secret_key_uses_local_fallback_when_allowed(self):
        settings_module, resolved_secret = self._reload_settings({
            'DJANGO_ENV': 'local',
            'DJANGO_ALLOW_LOCAL_SECRET_FALLBACK': '1',
        })

        self.assertEqual(resolved_secret, settings_module.LOCAL_SECRET_KEY_FALLBACK)
        self.assertEqual(settings_module.SECRET_KEY, settings_module.LOCAL_SECRET_KEY_FALLBACK)

    def test_secret_key_fails_fast_in_non_local_without_secret(self):
        with self.assertRaises(ImproperlyConfigured):
            self._reload_settings({
                'DJANGO_ENV': 'production',
                'DJANGO_ALLOW_LOCAL_SECRET_FALLBACK': '1',
            })
