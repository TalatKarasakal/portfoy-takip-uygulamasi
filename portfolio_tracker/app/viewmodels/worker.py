"""ViewModel'lerin uzun süren işleri için ortak, kontrollü QThread işçisi."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal

from app.utils.logger import redact_sensitive


class FunctionWorker(QThread):
    """Session/ORM taşımadan, immutable girdilerle bir fonksiyon çalıştırır."""

    result_ready = Signal(str, object)
    error_occurred = Signal(str, str)
    progress_changed = Signal(str, int)

    def __init__(self, tag: str, function: Callable[[], Any]) -> None:
        super().__init__()
        self.tag = tag
        self._function = function

    def run(self) -> None:
        if self.isInterruptionRequested():
            return
        self.progress_changed.emit(self.tag, 0)
        try:
            result = self._function()
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.error_occurred.emit(self.tag, redact_sensitive(exc))
            return
        if not self.isInterruptionRequested():
            self.progress_changed.emit(self.tag, 100)
            self.result_ready.emit(self.tag, result)


def stop_worker(worker: QThread | None, timeout_ms: int = 5000) -> None:
    """İşçiden kesilme ister ve Qt nesnesi yok edilmeden bitmesini bekler."""
    if worker is not None and worker.isRunning():
        worker.requestInterruption()
        worker.wait(timeout_ms)
