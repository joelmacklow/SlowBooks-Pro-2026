import os
import unittest
from unittest import mock

from scripts import bootstrap_database


class BootstrapDatabaseTests(unittest.TestCase):
    def test_bootstrap_env_sets_database_url_and_repo_root_pythonpath(self):
        with mock.patch.dict(os.environ, {"PYTHONPATH": "/existing/path"}, clear=False):
            env = bootstrap_database._bootstrap_env("sqlite:///tmp/test.db")

        self.assertEqual(env["DATABASE_URL"], "sqlite:///tmp/test.db")
        parts = env["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(parts[0], str(bootstrap_database.REPO_ROOT))
        self.assertIn("/existing/path", parts)

    def test_run_bootstrap_uses_python_module_alembic(self):
        calls = []

        def fake_run(command, cwd=None, env=None, check=None):
            calls.append((command, cwd, env, check))
            return None

        with mock.patch("scripts.bootstrap_database.subprocess.run", side_effect=fake_run):
            bootstrap_database.run_bootstrap("sqlite:///tmp/test.db")

        self.assertEqual(calls[0][0][:3], [bootstrap_database.sys.executable, "-m", "alembic"])
        self.assertEqual(calls[0][1], bootstrap_database.REPO_ROOT)
        self.assertEqual(calls[1][0], [bootstrap_database.sys.executable, "scripts/seed_database.py"])
        self.assertEqual(calls[1][1], bootstrap_database.REPO_ROOT)
        self.assertEqual(calls[0][2]["DATABASE_URL"], "sqlite:///tmp/test.db")
        self.assertTrue(calls[0][2]["PYTHONPATH"].split(os.pathsep)[0].endswith("SlowBooks-Pro-2026"))
        self.assertTrue(all(call[3] is True for call in calls))


if __name__ == "__main__":
    unittest.main()
