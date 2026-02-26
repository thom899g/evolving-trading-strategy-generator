"""
Configuration management for the evolving trading strategy system.
Centralized configuration with environment variable support.
"""

import os
import yaml
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import timedelta
import logging

@dataclass
class FirebaseConfig:
    """Firebase configuration"""
    project_id: str = os.getenv("FIREBASE_PROJECT_ID", "trading-evolution-dev")
    credentials_path: str = os.getenv("FIREBASE_CREDENTIALS", "./credentials/firebase_credentials.json")
    collection_strategies: str = "strategies"
    collection_markets: str = "markets"
    collection_performance: str = "performance_metrics"
    realtime_path: str = "realtime/streams"

@dataclass
class ExchangeConfig:
    """Exchange API configuration"""
    name: str = "binance"
    api_key: str = os.getenv("EXCHANGE_API_KEY", "")
    api_secret: str = os.getenv("EXCHANGE_API_SECRET", "")
    rate_limit: int = 1200  # requests per minute
    testnet: bool = os.getenv("EXCHANGE_TESTNET", "True").lower() == "true"

@dataclass
class DataConfig:
    """Data acquisition configuration"""
    timeframes: List[str] = field(default_factory=lambda: ["1m", "5m", "15m", "1h", "4h", "1d"])
    lookback_days: int = 365
    batch_size: int = 1000
    cache_ttl: int = 300  # seconds

@dataclass
class EvolutionConfig:
    """Genetic evolution configuration"""
    population_size: int = 100
    generations: int = 50
    mutation_rate: float = 0.15
    crossover_rate: float = 0.7
    elitism_count: int = 5
    fitness_metric: str = "sharpe_ratio"
    min_trades: int = 10

@dataclass
class BacktestConfig:
    """Backtesting configuration"""
    initial_capital: float = 10000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    risk_free_rate: float = 0.02
    max_drawdown_limit: float = 0.3

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    rotation: str = "10 MB"
    retention: str = "30 days"

class ConfigManager:
    """Centralized configuration manager"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.firebase = FirebaseConfig()
        self.exchange = ExchangeConfig()
        self.data = DataConfig()
        self.evolution = EvolutionConfig()
        self.backtest = BacktestConfig()
        self.logging = LoggingConfig()
        
        if config_path and os.path.exists(config_path):
            self._load_from_yaml(config_path)
        
        self._validate_config()
    
    def _load_from_yaml(self, config_path: str):
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                
            for section, values in config_data.items():
                if hasattr(self, section):
                    section_obj = getattr(self, section)
                    for key, value in values.items():
                        if hasattr(section_obj, key):
                            setattr(section_obj, key, value)
        except Exception as e:
            logging.warning(f"Failed to load YAML config: {e}")
    
    def _validate_config(self):
        """Validate configuration values"""
        assert self.evolution.population_size > 0, "Population size must be positive"
        assert 0 <= self.evolution.mutation_rate <= 1, "Mutation rate must be between 0 and 1"
        assert 0 <= self.backtest.commission_rate <= 0.1, "Commission rate must be reasonable"
        
        # Validate exchange configuration
        if not self.exchange.testnet:
            assert len(self.exchange.api_key) > 0, "API key required for live trading"
            assert len(self.exchange.api_secret) > 0, "API secret required for live trading"
    
    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return {
            'firebase': self.firebase.__dict__,
            'exchange': self.exchange.__dict__,
            'data': self.data.__dict__,
            'evolution': self.evolution.__dict__,
            'backtest': self.backtest.__dict__,
            'logging': self.logging.__dict__
        }

# Singleton instance
config = ConfigManager()