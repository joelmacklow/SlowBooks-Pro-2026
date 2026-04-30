import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)


class StartupStoragePermissionTests(unittest.TestCase):
    def test_storage_modules_do_not_require_writable_dirs_at_import(self):
        original_mkdir = Path.mkdir

        def guarded_mkdir(path_obj, *args, **kwargs):
            path_text = str(path_obj)
            if path_text.endswith("/app/static/uploads") or path_text.endswith("/backups"):
                raise PermissionError("storage not writable")
            return original_mkdir(path_obj, *args, **kwargs)

        for module_name in [
            "app.routes.uploads",
            "app.services.backup_service",
            "app.routes.backups",
        ]:
            sys.modules.pop(module_name, None)

        with mock.patch("pathlib.Path.mkdir", new=guarded_mkdir),              mock.patch("fastapi.dependencies.utils.ensure_multipart_is_installed", return_value=None):
            importlib.import_module("app.routes.uploads")
            importlib.import_module("app.services.backup_service")
            importlib.import_module("app.routes.backups")

    def test_main_module_no_longer_eagerly_creates_upload_dir(self):
        main_source = Path("app/main.py").read_text()

        self.assertNotIn("mkdir(", main_source)


if __name__ == "__main__":
    unittest.main()
