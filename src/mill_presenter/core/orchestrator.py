import numpy as np
from pathlib import Path
from typing import Optional, Callable
from PyQt6.QtCore import QThread, pyqtSignal
from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor
from mill_presenter.core.cache import ResultsCache
from mill_presenter.core.models import FrameDetections
from mill_presenter.core.tracker import BallTracker
from mill_presenter.utils.logging import get_logger

logger = get_logger(__name__)


class DetectionThread(QThread):
    """
    Background thread for running detection pipeline.
    
    Signals:
        progress(current_frame, total_frames): Emitted after each frame.
        finished(detections_path): Emitted on successful completion.
        error(message): Emitted on failure.
    """
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        video_path: str,
        config: dict,
        output_path: str,
        roi_mask: Optional[np.ndarray] = None,
        limit: Optional[int] = None,
        parent=None
    ):
        super().__init__(parent)
        self.video_path = video_path
        self.config = config
        self.output_path = output_path
        self.roi_mask = roi_mask
        self.limit = limit
        self._orchestrator: Optional[ProcessorOrchestrator] = None

    def run(self):
        """Execute detection pipeline in background."""
        loader = None
        try:
            # Initialize components
            loader = FrameLoader(self.video_path)
            processor = VisionProcessor(self.config)
            
            # Clear existing cache and create fresh
            cache = ResultsCache(self.output_path)
            cache.clear()
            
            self._orchestrator = ProcessorOrchestrator(loader, processor, cache)
            
            if self.roi_mask is not None:
                self._orchestrator.set_roi_mask(self.roi_mask)

            # Calculate total for progress
            total = loader.total_frames
            if self.limit is not None:
                total = min(self.limit, total)

            def progress_cb(pct: float):
                current = int(pct / 100 * total)
                self.progress.emit(current, total)

            self._orchestrator.run(progress_callback=progress_cb, limit=self.limit)
            self.finished.emit(self.output_path)

        except Exception as e:
            logger.exception("Detection failed")
            self.error.emit(str(e))
        finally:
            if loader:
                loader.close()

    def cancel(self):
        """Request cancellation of the detection pipeline."""
        if self._orchestrator:
            self._orchestrator.cancel()


class ProcessorOrchestrator:
    """
    Coordinates the detection pipeline.
    
    Responsibilities:
    1. Reads frames from FrameLoader.
    2. Feeds frames + ROI mask to VisionProcessor.
    3. Wraps results in FrameDetections.
    4. Saves results to ResultsCache.
    5. Reports progress and handles cancellation.
    """
    
    def __init__(self, loader: FrameLoader, processor: VisionProcessor, cache: ResultsCache):
        self.loader = loader
        self.processor = processor
        self.cache = cache
        self.roi_mask: Optional[np.ndarray] = None
        self._cancel_requested = False
        processor_config = getattr(processor, "config", None)
        if not isinstance(processor_config, dict):
            processor_config = {}

        self._tracking_enabled = bool(processor_config.get("tracking", {}).get("enabled", False))
        self._tracker: Optional[BallTracker] = (
            BallTracker.from_config(processor_config) if self._tracking_enabled else None
        )

    def set_roi_mask(self, mask: np.ndarray):
        """Sets the Region of Interest mask for processing."""
        self.roi_mask = mask

    def cancel(self):
        """Requests the processing loop to stop."""
        self._cancel_requested = True
        logger.info("Cancellation requested.")

    def run(self, progress_callback: Optional[Callable[[float], None]] = None, limit: Optional[int] = None):
        """
        Runs the detection pipeline on the entire video.
        
        Args:
            progress_callback: Function taking a float (0.0 - 100.0) to report progress.
            limit: Optional maximum number of frames to process.
        """
        self._cancel_requested = False
        total_frames = self.loader.total_frames
        if limit is not None and limit < total_frames:
            total_frames = limit
        
        logger.info(f"Starting processing for {total_frames} frames...")

        if self._tracking_enabled and self._tracker is not None:
            self._tracker.reset()
        
        for frame_idx, frame_img in self.loader.iter_frames():
            # Check cancellation
            if self._cancel_requested:
                logger.info("Processing cancelled by user.")
                break
            
            # Check limit
            if limit is not None and frame_idx >= limit:
                logger.info(f"Reached limit of {limit} frames.")
                break
                
            # 1. Process
            balls = self.processor.process_frame(frame_img, roi_mask=self.roi_mask)

            # 1.5 Assign persistent IDs (detection-time tracking)
            if self._tracking_enabled and self._tracker is not None:
                balls = self._tracker.update(frame_idx, balls)
            
            # 2. Wrap
            # Calculate timestamp based on frame index and FPS
            timestamp = frame_idx / self.loader.fps if self.loader.fps > 0 else 0.0
            
            detections = FrameDetections(
                frame_id=frame_idx,
                timestamp=timestamp,
                balls=balls
            )
            
            # 3. Save
            self.cache.save_frame(detections)
            
            # 4. Report Progress
            if progress_callback and total_frames > 0:
                progress = (frame_idx + 1) / total_frames * 100.0
                progress_callback(progress)
                
        logger.info("Processing finished.")
