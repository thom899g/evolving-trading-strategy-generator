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