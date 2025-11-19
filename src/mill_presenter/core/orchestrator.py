import numpy as np
from typing import Optional, Callable
from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor
from mill_presenter.core.cache import ResultsCache
from mill_presenter.core.models import FrameDetections
from mill_presenter.utils.logging import get_logger

logger = get_logger(__name__)

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

    def set_roi_mask(self, mask: np.ndarray):
        """Sets the Region of Interest mask for processing."""
        self.roi_mask = mask

    def cancel(self):
        """Requests the processing loop to stop."""
        self._cancel_requested = True
        logger.info("Cancellation requested.")

    def run(self, progress_callback: Optional[Callable[[float], None]] = None):
        """
        Runs the detection pipeline on the entire video.
        
        Args:
            progress_callback: Function taking a float (0.0 - 100.0) to report progress.
        """
        self._cancel_requested = False
        total_frames = self.loader.total_frames
        
        logger.info(f"Starting processing for {total_frames} frames...")
        
        for frame_idx, frame_img in self.loader.iter_frames():
            # Check cancellation
            if self._cancel_requested:
                logger.info("Processing cancelled by user.")
                break
                
            # 1. Process
            balls = self.processor.process_frame(frame_img, roi_mask=self.roi_mask)
            
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
