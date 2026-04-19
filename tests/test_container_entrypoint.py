import os
import unittest
from unittest import mock

from app import container_entrypoint


class ContainerEntrypointTests(unittest.TestCase):
    def test_bootstrap_setup_url_uses_port_and_token(self):
        with mock.patch.dict(os.environ, {"APP_PORT": "4123", "BOOTSTRAP_ADMIN_TOKEN": "abc xyz"}, clear=False):
            self.assertEqual(
                container_entrypoint.bootstrap_setup_url(),
                "http://localhost:4123/#/login?bootstrap_token=abc%20xyz",
            )

    def test_ensure_bootstrap_token_sets_value_when_missing(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            container_entrypoint.ensure_bootstrap_token()
            self.assertTrue(os.environ["BOOTSTRAP_ADMIN_TOKEN"])

    def test_scheduler_mode_reads_env_flag(self):
        with mock.patch.dict(os.environ, {"RUN_INVOICE_REMINDER_SCHEDULER": "true"}, clear=False):
            self.assertTrue(container_entrypoint.is_scheduler_mode())
        with mock.patch.dict(os.environ, {"RUN_INVOICE_REMINDER_SCHEDULER": "false"}, clear=False):
            self.assertFalse(container_entrypoint.is_scheduler_mode())


if __name__ == "__main__":
    unittest.main()
