import os
import sys
import types
import unittest

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

weasyprint_stub = types.ModuleType('weasyprint')
weasyprint_stub.HTML = object
sys.modules.setdefault('weasyprint', weasyprint_stub)


class StaffRoleTemplatePermissionsTests(unittest.TestCase):
    def test_staff_template_includes_requested_operational_permissions(self):
        from app.services.auth import ROLE_TEMPLATE_DEFINITIONS

        expected = {
            'companies.view',
            'contacts.manage',
            'contacts.view',
            'items.view',
            'purchasing.manage',
            'purchasing.view',
            'sales.manage',
            'sales.view',
        }
        self.assertEqual(ROLE_TEMPLATE_DEFINITIONS['staff']['permissions'], expected)


if __name__ == '__main__':
    unittest.main()
