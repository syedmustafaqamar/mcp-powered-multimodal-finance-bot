from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FinancialMetric(Base):
    """Structured finance facts available to the database agent."""

    __tablename__ = "financial_metrics"
    __table_args__ = (
        UniqueConstraint(
            "company",
            "period",
            "metric",
            name="uq_financial_metric_company_period_metric",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company: Mapped[str] = mapped_column(String(100), index=True)
    period: Mapped[str] = mapped_column(String(20), index=True)
    metric: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30))
    source: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
