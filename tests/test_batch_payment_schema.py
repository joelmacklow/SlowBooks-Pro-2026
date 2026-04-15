import unittest
from datetime import date


class BatchPaymentSchemaTests(unittest.TestCase):
    def test_batch_payment_schema_module_exposes_expected_request_fields(self):
        from app.schemas.batch_payments import BatchPaymentAllocationCreate, BatchPaymentCreate

        allocation_fields = BatchPaymentAllocationCreate.model_fields
        create_fields = BatchPaymentCreate.model_fields

        self.assertIn("customer_id", allocation_fields)
        self.assertIn("invoice_id", allocation_fields)
        self.assertIn("amount", allocation_fields)

        self.assertIn("date", create_fields)
        self.assertIn("deposit_to_account_id", create_fields)
        self.assertIn("method", create_fields)
        self.assertIn("reference", create_fields)
        self.assertIn("allocations", create_fields)

    def test_batch_payment_schema_accepts_ui_payload(self):
        from app.schemas.batch_payments import BatchPaymentCreate

        payload = BatchPaymentCreate.model_validate(
            {
                "date": "2026-04-15",
                "method": "check",
                "reference": "DEP-100",
                "deposit_to_account_id": 7,
                "allocations": [
                    {"customer_id": 1, "invoice_id": 2, "amount": "10.50"},
                ],
            }
        )

        self.assertEqual(payload.date, date(2026, 4, 15))
        self.assertEqual(payload.deposit_to_account_id, 7)
        self.assertEqual(str(payload.allocations[0].amount), "10.50")


if __name__ == "__main__":
    unittest.main()
