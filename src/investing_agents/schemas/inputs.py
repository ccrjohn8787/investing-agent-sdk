from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field, NonNegativeFloat, PositiveFloat


class Provenance(BaseModel):
    vendor: str = Field(default="unknown")
    retrieved_at: Optional[str] = None
    source_url: Optional[str] = None
    content_sha256: Optional[str] = None


class Macro(BaseModel):
    risk_free_curve: List[PositiveFloat] = Field(default_factory=list)  # by year
    erp: PositiveFloat = Field(default=0.05)
    country_risk: float = Field(default=0.0)


class Discounting(BaseModel):
    mode: str = Field(default="end", pattern=r"^(end|midyear)$")


class Leases(BaseModel):
    include: bool = Field(default=True)


class Drivers(BaseModel):
    sales_growth: List[float] = Field(default_factory=list)
    oper_margin: List[float] = Field(default_factory=list)
    stable_growth: float = Field(default=0.02)
    stable_margin: float = Field(default=0.10)


class InputsI(BaseModel):
    company: str
    ticker: str
    currency: str = Field(default="USD")
    asof_date: Optional[date] = None

    shares_out: PositiveFloat
    tax_rate: float = Field(ge=0.0, le=1.0, default=0.25)

    revenue_t0: NonNegativeFloat = 0.0
    net_debt: float = 0.0
    cash_nonop: float = 0.0

    drivers: Drivers
    sales_to_capital: List[PositiveFloat] = Field(default_factory=list)
    wacc: List[PositiveFloat] = Field(default_factory=list)

    macro: Macro = Field(default_factory=Macro)
    discounting: Discounting = Field(default_factory=Discounting)
    leases: Leases = Field(default_factory=Leases)

    provenance: Provenance = Field(default_factory=Provenance)

    model_config = {
        "arbitrary_types_allowed": True,
        "validate_assignment": True,
    }

    def horizon(self) -> int:
        lens = [
            len(self.drivers.sales_growth),
            len(self.drivers.oper_margin),
            len(self.sales_to_capital),
            len(self.wacc),
        ]
        if len(set(lens)) != 1:
            raise ValueError(f"Path length mismatch: {lens}")
        return lens[0]
