"""
Economic Systems Module

Resource markets, trading, and scarcity-driven agent behavior.
"""

from .resources import ResourceType, Resource, ResourcePool
from .market import Market, Trade, PriceHistory
from .agents import EconomicAgent, TradingStrategy

__all__ = [
    'ResourceType',
    'Resource',
    'ResourcePool',
    'Market',
    'Trade',
    'PriceHistory',
    'EconomicAgent',
    'TradingStrategy'
]
