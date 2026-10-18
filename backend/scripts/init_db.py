"""Create application tables and load the small finance demo dataset."""

from sqlalchemy import select

from app.core.database import SessionLocal, create_tables
from app.finance.models import FinancialMetric

DEMO_SOURCE = "Tesla Q2 2026 Update (official investor relations)"

DATA = [
    ("Tesla", "Q2-2026", "total_revenue", 28236, "USD_millions"),
    ("Tesla", "Q2-2026", "automotive_revenue", 20516, "USD_millions"),
    ("Tesla", "Q2-2026", "energy_revenue", 3139, "USD_millions"),
    ("Tesla", "Q2-2026", "services_and_other_revenue", 4581, "USD_millions"),
    ("Tesla", "Q2-2026", "gross_profit", 4751, "USD_millions"),
    ("Tesla", "Q2-2026", "gross_margin", 16.8, "percent"),
    ("Tesla", "Q2-2026", "operating_income", 398, "USD_millions"),
    ("Tesla", "Q2-2026", "operating_margin", 1.4, "percent"),
    ("Tesla", "Q2-2026", "gaap_net_income", 1114, "USD_millions"),
    ("Tesla", "Q2-2026", "diluted_gaap_eps", 0.32, "USD_per_share"),
    ("Tesla", "Q2-2026", "operating_cash_flow", 4697, "USD_millions"),
    ("Tesla", "Q2-2026", "capital_expenditures", 5789, "USD_millions"),
    ("Tesla", "Q2-2026", "free_cash_flow", -1092, "USD_millions"),
    ("Tesla", "Q2-2026", "cash_and_investments", 43524, "USD_millions"),
    ("Tesla", "Q2-2026", "total_vehicle_deliveries", 480126, "vehicles"),
    ("Tesla", "Q2-2026", "active_fsd_subscriptions", 1.48, "millions"),
    ("Tesla", "Q2-2026", "storage_deployed", 13.5, "GWh"),
]


def main() -> None:
    create_tables()

    with SessionLocal() as session:
        for company, period, metric, value, unit in DATA:
            existing = session.scalar(
                select(FinancialMetric).where(
                    FinancialMetric.company == company,
                    FinancialMetric.period == period,
                    FinancialMetric.metric == metric,
                )
            )
            if existing is not None:
                existing.value = value
                existing.unit = unit
                existing.source = DEMO_SOURCE
                continue

            session.add(
                FinancialMetric(
                    company=company,
                    period=period,
                    metric=metric,
                    value=value,
                    unit=unit,
                    source=DEMO_SOURCE,
                )
            )

        session.commit()

    print(f"Database initialized. Loaded {len(DATA)} Tesla Q2-2026 demo metrics.")


if __name__ == "__main__":
    main()
