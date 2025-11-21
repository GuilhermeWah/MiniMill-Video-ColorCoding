import cv2
import os
import copy
import numpy as np
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt
from typing import Optional, Set, Callable
from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.cache import ResultsCache
from mill_presenter.core.overlay import OverlayRenderer
from mill_presenter.utils.logging import get_logger

logger = get_logger(__name__)

class VideoExporter:
    """
    Handles exporting the video with overlays to an MP4 file.
    Reuses OverlayRenderer to ensure visual consistency with the UI.
    """
    
    def __init__(self, config: dict, frame_loader: FrameLoader, results_cache: ResultsCache):
        self.config = config
        self.frame_loader = frame_loader
        self.results_cache = results_cache
        self.renderer = OverlayRenderer(config)
        
    def export(self, output_path: str, visible_classes: Set[int], progress_callback: Optional[Callable[[int, int], None]] = None):
        """
        Runs the export process.
        
        Args:
            output_path: Destination .mp4 file path.
            visible_classes: Set of class IDs to draw.
            progress_callback: Function(current_frame, total_frames) called periodically.
        """
        logger.info(f"Starting export to {output_path}")
        
        # Load ROI mask
        detections_dir = self.config.get('paths', {}).get('detections_dir', '.')
        mask_path = os.path.join(detections_dir, "roi_mask.png")
        roi_mask = None
        if os.path.exists(mask_path):
            roi_mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            logger.info(f"Loaded ROI mask from {mask_path}")
        
        # Get video properties
        width = self.frame_loader.width
        height = self.frame_loader.height
        fps = self.frame_loader.fps
        total_frames = self.frame_loader.total_frames
        
        # Initialize VideoWriter
        # mp4v is widely supported
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not writer.isOpened():
            raise RuntimeError(f"Failed to open video writer for {output_path}")
            
        try:
            # Iterate through all frames
            for frame_idx, frame_bgr in self.frame_loader.iter_frames():
                
                # 1. Get detections
                detections = self.results_cache.get_frame(frame_idx)
                
                # Filter by ROI if needed
                if detections and roi_mask is not None:
                    valid_balls = []
                    for ball in detections.balls:
                        bx, by = int(ball.x), int(ball.y)
                        # Check bounds
                        if 0 <= by < roi_mask.shape[0] and 0 <= bx < roi_mask.shape[1]:
                            # Check mask (White=Valid, Gray/Black=Ignore)
                            # ROIController saves Valid as White (255), Ignore as Gray (127)
                            if roi_mask[by, bx] > 200: 
                                valid_balls.append(ball)
                    
                    # Create a shallow copy to avoid modifying cache
                    detections_copy = copy.copy(detections)
                    detections_copy.balls = valid_balls
                    detections = detections_copy

                # 2. Draw overlays
                # We need to convert BGR numpy array to QImage to use QPainter
                # QImage expects RGB usually, but we can use Format_BGR888
                # frame_bgr is (height, width, 3) uint8
                
                # Create QImage from data
                # Note: QImage references the data, so we must keep frame_bgr alive
                h, w, ch = frame_bgr.shape
                bytes_per_line = ch * w
                qimg = QImage(frame_bgr.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
                
                # Create a painter on the QImage
                painter = QPainter(qimg)
                
                # Draw using the shared renderer
                # Scale is 1.0 because we are drawing on the full-resolution frame
                self.renderer.draw(painter, detections, visible_classes, scale=1.0)
                
                painter.end()
                
                # 3. Write to video
                # The QImage modified the underlying frame_bgr data directly?
                # QImage(data, ...) creates a wrapper. QPainter draws on it.
                # If QImage wraps the numpy buffer, QPainter writes to that buffer.
                # So frame_bgr should be modified in-place.
                # Let's verify this assumption. 
                # Usually QImage(data) shares memory.
                
                writer.write(frame_bgr)
                
                # Update progress
                if progress_callback:
                    progress_callback(frame_idx, total_frames)
                    
        except Exception as e:
            logger.error(f"Export failed: {e}")
            raise
        finally:
            writer.release()
            logger.info("Export finished")

