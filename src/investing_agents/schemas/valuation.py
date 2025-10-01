from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ValuationV(BaseModel):
    pv_explicit: float
    pv_terminal: float
    pv_oper_assets: float

    net_debt: float = 0.0
    cash_nonop: float = 0.0

    equity_value: float
    shares_out: float
    value_per_share: float

    sensitivity_summary: Optional[dict] = None
    kernel_version: str = Field(default="ginzu-0.1")
    notes: Optional[str] = None
