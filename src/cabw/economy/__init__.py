"""
Economic Systems Module

Resource markets, trading, and scarcity-driven agent behavior.
"""

from .agents import EconomicAgent, TradingStrategy
from .market import Market, PriceHistory, Trade
from .resources import Resource, ResourcePool, ResourceType

__all__ = [
    "ResourceType",
    "Resource",
    "ResourcePool",
    "Market",
    "Trade",
    "PriceHistory",
    "EconomicAgent",
    "TradingStrategy",
]
