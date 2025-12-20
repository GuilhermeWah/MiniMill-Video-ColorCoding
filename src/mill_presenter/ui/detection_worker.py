# MillPresenter — Detection Worker

"""
Background worker for running detection pipeline with progress reporting.
"""

from typing import Optional
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal


class DetectionWorker(QObject):
    """
    Worker that runs ProcessorOrchestrator in a background thread.
    
    Signals:
        progress(int, int, str): (current, total, message)
        finished(bool, str): (success, cache_path or error message)
    """
    
    progress = Signal(int, int, str)
    finished = Signal(bool, str)
    
    def __init__(self, video_path: str, cache_path: str, drum_diameter_mm: float = 200.0):
        super().__init__()
        self._video_path = video_path
        self._cache_path = cache_path
        self._drum_diameter_mm = drum_diameter_mm
        self._cancelled = False
    
    def run(self) -> None:
        """Run the detection pipeline."""
        try:
            from mill_presenter.core.orchestrator import ProcessorOrchestrator
            
            self.progress.emit(0, 100, "Initializing...")
            
            orchestrator = ProcessorOrchestrator(
                self._video_path,
                self._cache_path,
                self._drum_diameter_mm
            )
            
            def on_progress(current: int, total: int) -> None:
                if self._cancelled:
                    orchestrator.cancel()
                pct = int(100 * current / max(1, total))
                self.progress.emit(current, total, f"Processing frame {current}/{total}")
            
            success = orchestrator.run(progress_callback=on_progress)
            
            if success:
                self.finished.emit(True, self._cache_path)
            else:
                self.finished.emit(False, "Processing cancelled")
                
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def cancel(self) -> None:
        """Request cancellation."""
        self._cancelled = True


class DetectionRunner:
    """
    Manages detection in a background thread.
    
    Usage:
        runner = DetectionRunner()
        runner.progress.connect(on_progress)
        runner.finished.connect(on_finished)
        runner.start(video_path, cache_path)
    """
    
    progress = Signal(int, int, str)
    finished = Signal(bool, str)
    
    def __init__(self):
        self._thread: Optional[QThread] = None
        self._worker: Optional[DetectionWorker] = None
    
    def start(self, video_path: str, cache_path: str, drum_diameter_mm: float = 200.0) -> None:
        """Start detection in background thread."""
        if self._thread is not None and self._thread.isRunning():
            return
        
        self._thread = QThread()
        self._worker = DetectionWorker(video_path, cache_path, drum_diameter_mm)
        self._worker.moveToThread(self._thread)
        
        # Connect signals
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        
        self._thread.start()
    
    def cancel(self) -> None:
        """Cancel ongoing detection."""
        if self._worker:
            self._worker.cancel()
    
    def _on_progress(self, current: int, total: int, msg: str) -> None:
        """Forward progress signal."""
        # This will be connected externally
        pass
    
    def _on_finished(self, success: bool, result: str) -> None:
        """Handle completion."""
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None
