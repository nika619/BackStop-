import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/backstop.db")

# Ensure local data directory exists if using SQLite
if DATABASE_URL.startswith("sqlite"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if "./" in db_path or "/" in db_path or "\\" in db_path:
        parent_dir = Path(db_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
else:
    engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    SQLModel.metadata.create_all(engine)
    from backstop.models import BankHealthTelemetry, MerchantPolicy
    with Session(engine) as session:
        # Seed default merchants if not existing
        if not session.get(MerchantPolicy, "merch_ecommerce_01"):
            session.add(
                MerchantPolicy(
                    merchant_id="merch_ecommerce_01",
                    name="Apex Retail Pvt Ltd (E-Commerce)",
                    quiet_start_hour=9,
                    quiet_end_hour=21,
                    max_attempts=3,
                    incentive_budget_paise=5000000,  # ₹50,000
                    incentive_spent_paise=0,
                    auto_recovery_enabled=True,
                )
            )
        if not session.get(MerchantPolicy, "merch_saas_sub_02"):
            session.add(
                MerchantPolicy(
                    merchant_id="merch_saas_sub_02",
                    name="CloudScale SaaS India (Subscriptions)",
                    quiet_start_hour=10,
                    quiet_end_hour=20,
                    max_attempts=2,
                    incentive_budget_paise=2500000,  # ₹25,000
                    incentive_spent_paise=0,
                    auto_recovery_enabled=True,
                )
            )
        # Seed default bank health telemetry
        banks = [
            ("HDFC", "HDFC Bank Ltd", 0.96, False),
            ("ICICI", "ICICI Bank Ltd", 0.94, False),
            ("SBI", "State Bank of India", 0.91, False),
            ("AXIS", "Axis Bank Ltd", 0.95, False),
        ]
        for b_code, b_name, s_rate, is_out in banks:
            if not session.get(BankHealthTelemetry, b_code):
                session.add(
                    BankHealthTelemetry(
                        bank_code=b_code,
                        bank_name=b_name,
                        success_rate=s_rate,
                        is_outage=is_out,
                    )
                )
        session.commit()


def get_session():
    with Session(engine) as session:
        yield session
