import logging
from typing import Callable, Dict, Optional, Tuple

from PyQt6.QtCore import QTimer

logger = logging.getLogger(__name__)


class Debouncer:
    _delay_cache: Dict[str, int] = {}

    def __init__(
            self,
            callback: Callable,
            delay_ms: Optional[int] = None,
            config_key: Optional[str] = None
    ):
        self._callback = callback
        self._config_key = config_key
        self._delay_ms = delay_ms if delay_ms is not None else self._get_delay_from_config(config_key)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._execute)
        self._pending_args: Optional[Tuple[tuple, dict]] = None

    @classmethod
    def _get_delay_from_config(cls, config_key: Optional[str]) -> int:
        if config_key is None:
            config_key = "default_delay"

        if config_key in cls._delay_cache:
            return cls._delay_cache[config_key]

        from ui.styles import get_ui_constant
        delay = get_ui_constant('debounce', config_key, 100)
        cls._delay_cache[config_key] = delay
        return delay

    @classmethod
    def clear_cache(cls):
        cls._delay_cache.clear()

    @property
    def delay_ms(self) -> int:
        return self._delay_ms

    @delay_ms.setter
    def delay_ms(self, value: int):
        self._delay_ms = value

    def trigger(self, *args, **kwargs):
        self._pending_args = (args, kwargs)
        self._timer.start(self._delay_ms)

    def cancel(self):
        self._timer.stop()
        self._pending_args = None

    def is_pending(self) -> bool:
        return self._timer.isActive()

    def _execute(self):
        if self._pending_args is not None:
            args, kwargs = self._pending_args
            self._callback(*args, **kwargs)
