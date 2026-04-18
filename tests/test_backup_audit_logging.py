import os
import sys
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base


class BackupAuditLoggingTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_make_backup_writes_audit_entry(self):
        from app.models.audit import AuditLog
        from app.models.backups import Backup
        from app.routes import backups as backups_route

        with self.Session() as db:
            def fake_create_backup(_db, notes=None):
                backup = Backup(filename='slowbooks_20260418_020201.sql', file_size=123, backup_type='manual', notes=notes)
                _db.add(backup)
                _db.commit()
                return {'success': True, 'filename': backup.filename, 'file_size': backup.file_size}

            with mock.patch.object(backups_route, 'create_backup', side_effect=fake_create_backup):
                result = backups_route.make_backup(db=db, auth={'user_id': 7})

            self.assertTrue(result['success'])
            audit = db.query(AuditLog).filter(AuditLog.table_name == 'backups', AuditLog.action == 'CREATE').one()
            self.assertEqual(audit.record_id, 1)
            self.assertEqual(audit.new_values['filename'], 'slowbooks_20260418_020201.sql')
            self.assertEqual(audit.new_values['actor_user_id'], 7)

    def test_download_backup_writes_audit_entry(self):
        from app.models.audit import AuditLog
        from app.models.backups import Backup
        from app.routes import backups as backups_route
        from app.services import backup_service

        with TemporaryDirectory() as tmpdir, self.Session() as db,              mock.patch.object(backup_service, 'BACKUP_DIR', Path(tmpdir)):
            backup = Backup(filename='slowbooks_20260418_020202.sql', file_size=11, backup_type='manual')
            db.add(backup)
            db.commit()
            (Path(tmpdir) / backup.filename).write_text('backup-data', encoding='utf-8')

            response = backups_route.download_backup(backup.filename, db=db, auth={'user_id': 8})

            self.assertEqual(response.filename, backup.filename)
            audit = db.query(AuditLog).filter(AuditLog.table_name == 'backups', AuditLog.action == 'DOWNLOAD').one()
            self.assertEqual(audit.record_id, backup.id)
            self.assertEqual(audit.new_values['filename'], backup.filename)
            self.assertEqual(audit.new_values['actor_user_id'], 8)

    def test_restore_backup_writes_audit_entry(self):
        from app.models.audit import AuditLog
        from app.models.backups import Backup
        from app.routes import backups as backups_route

        with self.Session() as db:
            backup = Backup(filename='slowbooks_20260418_020203.sql', file_size=11, backup_type='manual')
            db.add(backup)
            db.commit()

            with mock.patch.object(backups_route, 'restore_backup', return_value={'success': True, 'message': 'restored'}):
                result = backups_route.restore(backups_route.RestoreRequest(filename=backup.filename), db=db, auth={'user_id': 9})

            self.assertTrue(result['success'])
            audit = db.query(AuditLog).filter(AuditLog.table_name == 'backups', AuditLog.action == 'RESTORE').one()
            self.assertEqual(audit.record_id, backup.id)
            self.assertEqual(audit.new_values['filename'], backup.filename)
            self.assertEqual(audit.new_values['actor_user_id'], 9)


if __name__ == '__main__':
    unittest.main()
