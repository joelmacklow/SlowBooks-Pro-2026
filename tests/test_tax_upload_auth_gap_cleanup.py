import asyncio
import importlib
import inspect
import os
import sys
import types
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import Headers

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

weasyprint_stub = types.ModuleType('weasyprint')
weasyprint_stub.HTML = object
sys.modules.setdefault('weasyprint', weasyprint_stub)

from app.database import Base


class TaxUploadAuthGapCleanupTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def _load_uploads_route(self):
        sys.modules.pop('app.routes.uploads', None)
        with mock.patch('fastapi.dependencies.utils.ensure_multipart_is_installed', return_value=None):
            return importlib.import_module('app.routes.uploads')

    def _bootstrap_owner(self, db):
        from app.routes.auth import bootstrap_admin
        from app.schemas.auth import BootstrapAdminRequest

        return bootstrap_admin(BootstrapAdminRequest(
            email='owner@example.com',
            password='supersecret',
            full_name='Owner User',
        ), db=db)

    def _create_staff_user(self, db, owner_token):
        from app.routes.auth import create_user, login
        from app.schemas.auth import LoginRequest, UserCreateRequest
        from app.services.auth import require_permissions

        owner_auth = require_permissions('users.manage')(db=db, authorization=f'Bearer {owner_token}')
        create_user(UserCreateRequest(
            email='staff@example.com',
            password='staffsecret',
            full_name='Staff User',
            role_key='staff',
            allow_permissions=['accounts.view'],
            deny_permissions=[],
        ), db=db, auth=owner_auth)
        return login(LoginRequest(email='staff@example.com', password='staffsecret'), db=db)

    def test_schedule_c_and_tax_mapping_endpoints_are_disabled_for_nz(self):
        from app.routes.tax import create_mapping, list_mappings, schedule_c_csv, schedule_c_report
        from app.schemas.tax import TaxMappingCreate

        for call in [
            lambda: schedule_c_report(),
            lambda: schedule_c_csv(),
            lambda: list_mappings(),
            lambda: create_mapping(TaxMappingCreate(account_id=1, tax_line='Schedule C, Line 1')),
        ]:
            with self.assertRaises(HTTPException) as ctx:
                call()
            self.assertEqual(ctx.exception.status_code, 410)
            self.assertIn('SlowBooks NZ', ctx.exception.detail)

    def test_logo_upload_requires_settings_manage_and_succeeds_for_authorized_user(self):
        from app.models.settings import Settings
        from app.services.auth import require_permissions

        uploads_route = self._load_uploads_route()
        self.assertIn('auth', inspect.signature(uploads_route.upload_logo).parameters)

        with self.Session() as db:
            owner = self._bootstrap_owner(db)
            staff = self._create_staff_user(db, owner.token)

            with self.assertRaises(HTTPException) as unauth_ctx:
                require_permissions('settings.manage')(db=db, authorization=None)
            self.assertEqual(unauth_ctx.exception.status_code, 401)

            with self.assertRaises(HTTPException) as staff_ctx:
                require_permissions('settings.manage')(db=db, authorization=f'Bearer {staff.token}')
            self.assertEqual(staff_ctx.exception.status_code, 403)

            owner_auth = require_permissions('settings.manage')(db=db, authorization=f'Bearer {owner.token}')
            upload = UploadFile(
                file=BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'),
                filename='logo.png',
                headers=Headers({'content-type': 'image/png'}),
            )
            with TemporaryDirectory() as tmpdir, mock.patch.object(uploads_route, 'UPLOAD_DIR', Path(tmpdir)):
                result = asyncio.run(uploads_route.upload_logo(file=upload, db=db, auth=owner_auth))
                saved = Path(tmpdir) / 'company_logo.png'
                setting = db.query(Settings).filter(Settings.key == 'company_logo_path').one()
                data_setting = db.query(Settings).filter(Settings.key == 'company_logo_data_uri').one()
                self.assertEqual(result['path'], '/static/uploads/company_logo.png')
                self.assertEqual(setting.value, '/static/uploads/company_logo.png')
                self.assertTrue(data_setting.value.startswith('data:image/png;base64,'))
                self.assertTrue(saved.exists())

    def test_logo_upload_rejects_svg_with_aligned_message(self):
        uploads_route = self._load_uploads_route()

        with self.Session() as db:
            owner = self._bootstrap_owner(db)
            from app.services.auth import require_permissions
            owner_auth = require_permissions('settings.manage')(db=db, authorization=f'Bearer {owner.token}')
            upload = UploadFile(
                file=BytesIO(b'<svg></svg>'),
                filename='logo.svg',
                headers=Headers({'content-type': 'image/svg+xml'}),
            )
            with self.assertRaises(HTTPException) as ctx:
                asyncio.run(uploads_route.upload_logo(file=upload, db=db, auth=owner_auth))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn('png', ctx.exception.detail.lower())
        self.assertIn('gif', ctx.exception.detail.lower())
        self.assertNotIn('svg', ctx.exception.detail.lower())


if __name__ == '__main__':
    unittest.main()
