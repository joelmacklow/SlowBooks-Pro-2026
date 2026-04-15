import os
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

weasyprint_stub = types.ModuleType('weasyprint')
weasyprint_stub.HTML = object
sys.modules.setdefault('weasyprint', weasyprint_stub)

from app.database import Base


class BackupPathHardeningTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_list_backups_ignores_invalid_stored_filenames(self):
        from app.models.backups import Backup
        from app.routes import backups as backups_route
        from app.services import backup_service

        with TemporaryDirectory() as tmpdir, self.Session() as db, \
             mock.patch.object(backup_service, 'BACKUP_DIR', Path(tmpdir)):
            valid_name = 'slowbooks_20260415_020202.sql'
            (Path(tmpdir) / valid_name).write_text('backup-data', encoding='utf-8')
            db.add(Backup(filename=valid_name, file_size=11, backup_type='manual'))
            db.add(Backup(filename='../outside.sql', file_size=99, backup_type='manual'))
            db.commit()

            backups = backups_route.list_backups(db=db, auth={'user_id': 1})

        self.assertEqual([item['filename'] for item in backups], [valid_name])

    def test_download_backup_rejects_path_traversal(self):
        from fastapi import HTTPException
        from app.routes import backups as backups_route

        with TemporaryDirectory() as tmpdir:
            with self.assertRaises(HTTPException) as ctx:
                backups_route.download_backup('../secrets.txt', auth={'user_id': 1})

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn('invalid', str(ctx.exception.detail).lower())

    def test_restore_backup_rejects_invalid_filename_without_subprocess(self):
        from app.services import backup_service

        with TemporaryDirectory() as tmpdir, self.Session() as db, \
             mock.patch.object(backup_service, 'BACKUP_DIR', Path(tmpdir)), \
             mock.patch.object(backup_service.subprocess, 'run') as run_mock:
            result = backup_service.restore_backup(db, '../outside.dump')

        self.assertFalse(result['success'])
        self.assertEqual(result['status_code'], 400)
        self.assertIn('invalid', result['error'].lower())
        run_mock.assert_not_called()

    def test_resolve_backup_path_accepts_managed_backup_file(self):
        from app.services import backup_service

        with TemporaryDirectory() as tmpdir, mock.patch.object(backup_service, 'BACKUP_DIR', Path(tmpdir)):
            expected = Path(tmpdir) / 'slowbooks_20260415_010101.sql'
            expected.write_text('backup-data', encoding='utf-8')

            resolved = backup_service.resolve_backup_path(expected.name)

        self.assertEqual(resolved, expected)


if __name__ == '__main__':
    unittest.main()
