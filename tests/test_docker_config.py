import importlib
import os
import runpy
import sys
import unittest
from pathlib import Path


class DockerConfigTests(unittest.TestCase):
    def test_database_url_takes_precedence_over_postgres_parts(self):
        import app.config as config

        original = os.environ.copy()
        try:
            os.environ["DATABASE_URL"] = "postgresql://alice:secret@db.example.com:5433/customdb"
            os.environ["POSTGRES_HOST"] = "ignored-host"
            os.environ["POSTGRES_PORT"] = "9999"
            os.environ["POSTGRES_DB"] = "ignored-db"
            os.environ["POSTGRES_USER"] = "ignored-user"
            os.environ["POSTGRES_PASSWORD"] = "ignored-pass"
            os.environ["POSTGRES_SSLMODE"] = "require"

            config = importlib.reload(config)

            self.assertEqual(config.DATABASE_URL, "postgresql://alice:secret@db.example.com:5433/customdb")
        finally:
            os.environ.clear()
            os.environ.update(original)
            importlib.reload(config)

    def test_database_url_builds_from_postgres_parts_when_blank(self):
        import app.config as config

        original = os.environ.copy()
        try:
            os.environ["DATABASE_URL"] = ""
            os.environ["POSTGRES_HOST"] = "postgres"
            os.environ["POSTGRES_PORT"] = "5432"
            os.environ["POSTGRES_DB"] = "slowbooks"
            os.environ["POSTGRES_USER"] = "slowbooks"
            os.environ["POSTGRES_PASSWORD"] = "replace-with-a-long-random-password"
            os.environ["POSTGRES_SSLMODE"] = "disable"

            config = importlib.reload(config)

            self.assertEqual(
                config.DATABASE_URL,
                "postgresql://slowbooks:replace-with-a-long-random-password@postgres:5432/slowbooks?sslmode=disable",
            )
        finally:
            os.environ.clear()
            os.environ.update(original)
            importlib.reload(config)

    def test_build_database_url_uses_safer_non_legacy_fallback_defaults(self):
        import app.config as config

        self.assertEqual(
            config.build_database_url(env={}),
            "postgresql://slowbooks:replace-with-a-long-random-password@localhost:5432/slowbooks?sslmode=disable",
        )

    def test_resolve_cors_origins_uses_explicit_loopback_safe_defaults(self):
        import app.config as config

        self.assertEqual(
            config.resolve_cors_origins(env={}),
            [
                "http://localhost:3001",
                "http://127.0.0.1:3001",
            ],
        )

    def test_resolve_cors_origins_honors_env_override(self):
        import app.config as config

        env = {"CORS_ALLOW_ORIGINS": "https://app.example.com, https://admin.example.com "}
        self.assertEqual(
            config.resolve_cors_origins(env=env),
            ["https://app.example.com", "https://admin.example.com"],
        )

    def test_docker_assets_and_env_keys_exist(self):
        root = Path(__file__).resolve().parent.parent
        env_example = (root / ".env.example").read_text()
        dockerfile_text = (root / "Dockerfile").read_text()
        backup_script = (root / "scripts" / "backup.sh").read_text()
        entrypoint_script = (root / "scripts" / "docker-entrypoint.sh").read_text()

        self.assertTrue((root / "Dockerfile").exists())
        self.assertTrue((root / "docker-compose.yml").exists())
        self.assertTrue((root / ".dockerignore").exists())
        self.assertTrue((root / "scripts" / "docker-entrypoint.sh").exists())
        self.assertTrue((root / "scripts" / "docker" / "docker-entrypoint.sh").exists())
        self.assertIn("PYTHONPATH=/app", dockerfile_text)
        self.assertIn('CMD ["/bin/sh", "/app/scripts/docker-entrypoint.sh"]', dockerfile_text)
        self.assertIn('USER slowbooks', dockerfile_text)
        self.assertIn('set -eo pipefail', backup_script)
        self.assertIn('mkdir -p /app/backups /app/app/static/uploads 2>/dev/null || true', entrypoint_script)
        compose_text = (root / "docker-compose.yml").read_text()
        self.assertIn("image: postgres:18", compose_text)
        self.assertIn("postgres_data:/var/lib/postgresql", compose_text)
        self.assertNotIn("./data/postgres:/var/lib/postgresql/data", compose_text)
        self.assertIn("volumes:\n  postgres_data:", compose_text)
        self.assertIn("./:/app:Z", compose_text)
        self.assertNotIn('POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-bookkeeper}', compose_text)
        self.assertNotIn('APP_DEBUG: ${APP_DEBUG:-true}', compose_text)
        self.assertNotIn('      - "${POSTGRES_PORT:-5432}:5432"', compose_text)
        self.assertIn('POSTGRES_PASSWORD: ${POSTGRES_PASSWORD?set POSTGRES_PASSWORD in your .env or environment}', compose_text)
        self.assertIn('APP_DEBUG: ${APP_DEBUG:-false}', compose_text)

        for key in (
            "DATABASE_URL=",
            "POSTGRES_HOST=",
            "POSTGRES_PORT=",
            "POSTGRES_DB=",
            "POSTGRES_USER=",
            "POSTGRES_PASSWORD=",
            "POSTGRES_SSLMODE=",
            "CORS_ALLOW_ORIGINS=",
        ):
            self.assertIn(key, env_example)
        self.assertIn("POSTGRES_PASSWORD=replace-with-a-long-random-password", env_example)
        self.assertIn("APP_DEBUG=false", env_example)
        self.assertNotIn("POSTGRES_PASSWORD=bookkeeper", env_example)

    def test_docs_call_for_explicit_password_setup_and_non_published_postgres(self):
        root = Path(__file__).resolve().parent.parent
        readme = (root / "README.md").read_text()
        install = (root / "INSTALL.md").read_text()

        self.assertIn("set POSTGRES_PASSWORD to a long random secret", readme)
        self.assertIn("Postgres is not published to the host by default", readme)
        self.assertIn("APP_DEBUG=false", readme)
        self.assertIn("CORS_ALLOW_ORIGINS", readme)
        self.assertIn("set POSTGRES_PASSWORD to a long random secret", install)
        self.assertIn("Postgres is not published to the host by default", install)
        self.assertIn("CORS_ALLOW_ORIGINS", install)

    def test_bootstrap_database_script_can_import_app_when_run_as_script(self):
        root = Path(__file__).resolve().parent.parent
        script = root / "scripts" / "bootstrap_database.py"
        original_cwd = Path.cwd()
        original_path = sys.path[:]

        try:
            os.chdir(root)
            sys.path = [str(script.parent)] + [entry for entry in original_path if Path(entry or ".").resolve() != root]
            namespace = runpy.run_path(str(script), run_name="bootstrap_database_test")
            self.assertIn("run_bootstrap", namespace)
        finally:
            os.chdir(original_cwd)
            sys.path = original_path


if __name__ == "__main__":
    unittest.main()
