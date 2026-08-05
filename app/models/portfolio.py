from pydantic import Field

from app.models.base import BaseModel
from app.models.holdings import Holding


class PortfolioSummary(BaseModel):
    total_value: float
    cash_balance: float
    day_change: float
    day_change_percent: float
    total_return: float
    total_return_percent: float
    holdings: list[Holding] = Field(default_factory=list)
    top_holdings: list[Holding] = Field(default_factory=list)
