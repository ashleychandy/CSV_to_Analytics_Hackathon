from datetime import datetime
from typing import Dict, Any

class ProcessingMonitor:
    def __init__(self):
        self._status = "Idle"
        self._processed_count = 0
        self._processing_time = 0.0
        self._last_update = None
        self._error_count = 0

    def update_status(self, status: str) -> None:
        self._status = status
        self._last_update = datetime.utcnow()

    def increment_processed(self, count: int = 1) -> None:
        self._processed_count += count
        self._last_update = datetime.utcnow()

    def reset_processed_count(self) -> None:
        self._processed_count = 0
        self._last_update = datetime.utcnow()

    def update_processing_time(self, time_in_seconds: float) -> None:
        self._processing_time = time_in_seconds
        self._last_update = datetime.utcnow()

    def get_status(self) -> Dict[str, Any]:
        return {
            "status": self._status,
            "processed_count": self._processed_count,
            "processing_time": self._processing_time,
            "last_update": self._last_update,
            "error_count": self._error_count
        }
        self._last_update = datetime.utcnow()