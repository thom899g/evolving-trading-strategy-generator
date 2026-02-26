# Evolving Trading Strategy Generator

## Objective
This system leverages advanced machine learning to autonomously generate and optimize trading strategies, adapting in real-time to market dynamics through continuous learning and evolution.

## Strategy
Develop ML algorithms to create diverse trading strategies, simulate performance across varied market scenarios, and employ reinforcement learning for continuous optimization based on outcomes.

## Execution Output
SUMMARY: I've designed and implemented a comprehensive trading strategy evolution system with a modular architecture, rigorous error handling, and full Firebase integration for state management. The system features data acquisition, feature engineering, strategy generation using genetic algorithms, backtesting, and real-time adaptation capabilities.

OUTPUT:

### FILE: requirements.txt
```
# Core dependencies
pandas>=2.0.0
numpy>=1.24.0
ccxt>=4.0.0
firebase-admin>=6.2.0
scikit-learn>=1.3.0
ta-lib>=0.4.0

# Data processing & ML
joblib>=1.3.0
scipy>=1.11.0
statsmodels>=0.14.0

# API & Web
requests>=2.31.0
websocket-client>=1.6.0

# Utilities
python-dotenv>=1.0.0
loguru>=0.7.0
pyyaml>=6.0
pytz>=2023.3
```

### FILE: config.py
```python
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
```

### FILE: firebase_client.py
```python
"""
Firebase client for state management, real-time data streaming, and strategy persistence.
Implements robust error handling and connection management.
"""

import firebase_admin
from firebase_admin import credentials, firestore, db
from google.cloud.firestore_v1.base_query import FieldFilter
from typing import Dict, List, Optional, Any, Callable
import logging
from datetime import datetime
import json
import time
from dataclasses import asdict
import threading
from queue import Queue

class FirebaseClient:
    """Firebase client for the trading evolution system"""
    
    def __init__(self, config):
        self.config = config
        self.app = None
        self.db = None
        self.realtime_db = None
        self._connected = False
        self._listeners = {}
        self._lock = threading.RLock()
        self._reconnect_attempts = 0
        self.max_reconnect_