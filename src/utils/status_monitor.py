from datetime import datetime
from typing import Optional

class ProcessingMonitor:
    def __init__(self):
        self._status: str = "Idle"
        self._last_update: Optional[datetime] = None
        self._processed_count: int = 0
        self._processing_time: float = 0.0

    def update_status(self, status: str):
        self._status = status
        self._last_update = datetime.utcnow()

    def get_status(self) -> dict:
        return {
            "status": self._status,
            "last_update": self._last_update,
            "processed_count": self._processed_count,
            "processing_time": self._processing_time
        }

    def increment_processed(self, count: int = 1):
        self._processed_count += count

    def update_processing_time(self, seconds: float):
        self._processing_time = seconds 