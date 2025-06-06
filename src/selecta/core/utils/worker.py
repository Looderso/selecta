from collections.abc import Callable
from typing import Any, Self

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal, pyqtSlot


class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread."""

    started = pyqtSignal()
    finished = pyqtSignal()
    error = pyqtSignal(str)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)


class Worker(QRunnable):
    """Worker thread for running background tasks."""

    def __init__(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Initialize the worker with the function to run.

        Args:
            fn: The function to run in the worker thread
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
        """
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Execute the function with the provided arguments."""
        try:
            self.signals.started.emit()
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit()


class ThreadManager:
    """Manages a pool of worker threads."""

    _instance = None

    def __new__(cls) -> Self:
        """Create a singleton instance of ThreadManager."""
        if cls._instance is None:
            # Create the instance first
            cls._instance = super().__new__(cls)
            # Then initialize its attributes
            cls._instance.thread_pool = QThreadPool()  # type: ignore
            # Set a sensible maximum based on CPU cores
            cls._instance.thread_pool.setMaxThreadCount(  # type: ignore
                max(4, QThreadPool.globalInstance().maxThreadCount())  # type: ignore
            )
        return cls._instance

    def run_task(self, fn: Callable, *args: Any, **kwargs: Any) -> Worker:
        """Run a task in a background thread.

        Args:
            fn: The function to run
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            Worker instance with signal connections
        """
        worker = Worker(fn, *args, **kwargs)
        self.thread_pool.start(worker)  # type: ignore
        return worker
