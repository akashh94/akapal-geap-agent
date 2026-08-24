from abc import ABC, abstractmethod

from app.models.account import Account
from app.models.holdings import Holding
from app.models.market import MarketIndex
from app.models.portfolio import PortfolioSummary
from app.models.quote import Quote
from app.models.sector import SectorAllocation


class BrokerageService(ABC):
    """
    Abstract interface for all brokerage providers.

    Agents and tools depend on this interface instead of a concrete
    brokerage implementation.
    """

    @abstractmethod
    def get_accounts(self) -> list[Account]: ...

    @abstractmethod
    def get_portfolio_summary(self) -> PortfolioSummary: ...

    @abstractmethod
    def get_holdings(self) -> list[Holding]: ...

    @abstractmethod
    def get_sector_allocation(self) -> list[SectorAllocation]: ...

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote | None: ...

    @abstractmethod
    def get_market_summary(self) -> list[MarketIndex]: ...

    @abstractmethod
    def get_faq(self) -> list[dict[str, str]]: ...
