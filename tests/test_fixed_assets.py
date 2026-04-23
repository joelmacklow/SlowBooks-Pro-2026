import os
import sys
import types
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

weasyprint_stub = types.ModuleType("weasyprint")
weasyprint_stub.HTML = object
sys.modules.setdefault("weasyprint", weasyprint_stub)

from app.database import Base
from app.models.accounts import Account, AccountType
from app.models.settings import Settings


class FixedAssetsTests(unittest.TestCase):
    def setUp(self):
        import app.models  # noqa: F401

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.Session = sessionmaker(bind=engine)

    def test_register_run_depreciation_and_dispose_fixed_asset(self):
        from app.routes.fixed_assets import create_fixed_asset, create_fixed_asset_type, dispose_fixed_asset, run_fixed_asset_depreciation
        from app.services.fixed_assets import asset_payload
        from app.models.fixed_assets import FixedAsset

        with self.Session() as db:
            bank = Account(name="Business Bank", account_number="090", account_type=AccountType.ASSET, is_active=True, balance=Decimal("5000.00"))
            vehicle_asset = Account(name="Motor Vehicles", account_number="730", account_type=AccountType.ASSET, is_active=True)
            acc_dep = Account(name="Less Accumulated Depreciation on Motor Vehicles", account_number="731", account_type=AccountType.ASSET, is_active=True)
            dep_exp = Account(name="Depreciation", account_number="416", account_type=AccountType.EXPENSE, is_active=True)
            other_income = Account(name="Other Revenue", account_number="260", account_type=AccountType.INCOME, is_active=True)
            general_expense = Account(name="General Expenses", account_number="429", account_type=AccountType.EXPENSE, is_active=True)
            db.add_all([bank, vehicle_asset, acc_dep, dep_exp, other_income, general_expense])
            db.commit()
            db.add_all([
                Settings(key="system_account_default_sales_income_id", value=str(other_income.id)),
                Settings(key="system_account_default_expense_id", value=str(general_expense.id)),
                Settings(key="financial_year_start", value="04-01"),
            ])
            db.commit()

            asset_type = create_fixed_asset_type({
                "name": "Motor Vehicles",
                "asset_account_id": vehicle_asset.id,
                "accumulated_depreciation_account_id": acc_dep.id,
                "depreciation_expense_account_id": dep_exp.id,
                "default_depreciation_method": "sl",
                "default_calculation_basis": "rate",
                "default_rate": "20.0",
            }, db=db)

            asset = create_fixed_asset({
                "name": "2007 BMW 123D",
                "asset_type_id": asset_type["id"],
                "purchase_date": "2026-04-01",
                "purchase_price": "1200.00",
                "depreciation_start_date": "2026-04-01",
                "depreciation_method": "sl",
                "calculation_basis": "rate",
                "rate": "20.0",
                "acquisition_method": "cash",
                "offset_account_id": bank.id,
            }, db=db)

            run = run_fixed_asset_depreciation(run_date=date(2027, 3, 31), db=db)
            self.assertEqual(run["assets_updated"], 1)
            self.assertEqual(run["total_depreciation"], 240.0)

            row = db.query(FixedAsset).filter(FixedAsset.id == asset["id"]).one()
            detail = asset_payload(db, row)
            self.assertEqual(detail["book_value"], 960.0)
            self.assertEqual(detail["accumulated_depreciation"], 240.0)

            disposed = dispose_fixed_asset(row.id, {
                "disposal_date": "2027-03-31",
                "sale_price": "1000.00",
                "disposal_costs": "10.00",
                "disposal_account_id": bank.id,
            }, db=db)

        self.assertEqual(disposed["status"], "disposed")
        self.assertEqual(round(disposed["gain_loss"], 2), 30.0)

    def test_fixed_asset_reconciliation_and_csv_import(self):
        from app.models.fixed_assets import FixedAsset, FixedAssetType
        from app.services.fixed_assets import fixed_asset_reconciliation, import_assets_from_csv

        with self.Session() as db:
            asset_account = Account(name="Office Equipment", account_number="710", account_type=AccountType.ASSET, is_active=True)
            acc_dep = Account(name="Less Accumulated Depreciation on Office Equipment", account_number="711", account_type=AccountType.ASSET, is_active=True)
            dep_exp = Account(name="Depreciation", account_number="416", account_type=AccountType.EXPENSE, is_active=True)
            db.add_all([asset_account, acc_dep, dep_exp])
            db.commit()
            db.add_all([
                Settings(key="system_account_fixed_asset_accumulated_depreciation_id", value=str(acc_dep.id)),
                Settings(key="system_account_fixed_asset_depreciation_expense_id", value=str(dep_exp.id)),
            ])
            db.commit()
            asset_type = FixedAssetType(
                name="Computer Equipment",
                asset_account_id=asset_account.id,
                accumulated_depreciation_account_id=acc_dep.id,
                depreciation_expense_account_id=dep_exp.id,
            )
            db.add(asset_type)
            db.commit()
            db.add(FixedAsset(
                asset_number="FA-0001",
                name="Laptop Fleet",
                asset_type_id=asset_type.id,
                purchase_date=date(2026, 4, 1),
                purchase_price=Decimal("2000.00"),
                depreciation_start_date=date(2026, 4, 1),
                depreciation_method="sl",
                calculation_basis="rate",
                rate=Decimal("20.0"),
                opening_accumulated_depreciation=Decimal("500.00"),
                accumulated_depreciation=Decimal("100.00"),
                acquisition_method="opening_balance",
            ))
            db.commit()

            report = fixed_asset_reconciliation(db, date(2026, 4, 30))
            self.assertEqual(report["total_cost"], 2000.0)
            self.assertEqual(report["total_accumulated_depreciation"], 600.0)
            self.assertEqual(report["total_book_value"], 1400.0)

            csv_text = "*AssetName,*AssetNumber,AssetStatus,PurchaseDate,PurchasePrice,AssetType,Description,TrackingCategory1,TrackingOption1,TrackingCategory2,TrackingOption2,SerialNumber,WarrantyExpiry,Book_DepreciationStartDate,Book_CostLimit,Book_ResidualValue,Book_DepreciationMethod,Book_AveragingMethod,Book_Rate,Book_EffectiveLife,Book_OpeningBookAccumulatedDepreciation,Book_BookValue,AccumulatedDepreciation,InvestmentBoost,DepreciationToDate,DisposalDate\n" \
                "Imported Printer,FA-0051,Registered,2024-09-02,6082.61,Motor Vehicles,, , , , ,SN-1,,2024-09-02,,,Diminishing value,Full month,30.0,,0.00,3512.70,2569.91,,2026-03-31,\n"
            result = import_assets_from_csv(db, csv_text)

        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["created_asset_types"], 1)

    def test_sample_fixed_asset_csv_import_fixture_loads_multiple_assets(self):
        from app.models.fixed_assets import FixedAsset
        from app.services.fixed_assets import import_assets_from_csv

        fixture_path = Path(__file__).with_name("fixed_assets_sample_import.csv")
        csv_text = fixture_path.read_text(encoding="utf-8-sig")

        with self.Session() as db:
            asset_account = Account(name="Office Equipment", account_number="710", account_type=AccountType.ASSET, is_active=True)
            acc_dep = Account(name="Less Accumulated Depreciation on Office Equipment", account_number="711", account_type=AccountType.ASSET, is_active=True)
            dep_exp = Account(name="Depreciation", account_number="416", account_type=AccountType.EXPENSE, is_active=True)
            db.add_all([asset_account, acc_dep, dep_exp])
            db.commit()
            db.add_all([
                Settings(key="system_account_fixed_asset_accumulated_depreciation_id", value=str(acc_dep.id)),
                Settings(key="system_account_fixed_asset_depreciation_expense_id", value=str(dep_exp.id)),
            ])
            db.commit()

            result = import_assets_from_csv(db, csv_text)
            rows = db.query(FixedAsset).order_by(FixedAsset.asset_number).all()

        self.assertEqual(result["imported"], 6)
        self.assertEqual(result["errors"], [])
        self.assertGreaterEqual(result["created_asset_types"], 4)
        self.assertEqual(rows[0].asset_number, "FA-1001")
        self.assertEqual(rows[-1].asset_number, "FA-1006")
        self.assertEqual(rows[4].status.value, "disposed")


if __name__ == "__main__":
    unittest.main()
