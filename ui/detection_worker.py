"""
Detection Worker

Background thread for running detection pipeline.
Supports both preview (single frame) and batch (all frames) modes.
"""

import cv2
import numpy as np
from typing import Optional, Dict, Any, List
from pathlib import Path
import json
import time

from PySide6.QtCore import QObject, QThread, Signal, QTimer


class DetectionParams:
    """Detection parameters that can be tuned."""
    
    # Default values (proven from testing)
    DEFAULTS = {
        "blur_kernel": 7,        # Proven: 7 works well for median blur
        "canny_low": 50,         # Standard low threshold
        "canny_high": 150,       # Standard high threshold
        "hough_dp": 1.0,         # Most accurate (1.0 = same as input)
        "hough_min_dist": 15,    # Allow tighter bead packing
        "hough_param1": 50,      # Canny high threshold for HoughCircles
        "hough_param2": 25,      # Balanced sensitivity
        "min_radius_px": 8,      # ~4mm beads at typical resolution
        "max_radius_px": 50,     # ~10mm beads at typical resolution
    }
    
    def __init__(self, **kwargs):
        for key, default in self.DEFAULTS.items():
            setattr(self, key, kwargs.get(key, default))
    
    def to_dict(self) -> dict:
        return {key: getattr(self, key) for key in self.DEFAULTS}
    
    @classmethod
    def from_dict(cls, data: dict) -> "DetectionParams":
        return cls(**{k: v for k, v in data.items() if k in cls.DEFAULTS})
    
    def copy(self) -> "DetectionParams":
        return DetectionParams(**self.to_dict())
    
    def __eq__(self, other):
        if not isinstance(other, DetectionParams):
            return False
        return self.to_dict() == other.to_dict()


class PreviewWorker(QObject):
    """
    Worker for single-frame preview detection.
    Runs detection on one frame and returns results quickly.
    """
    
    finished = Signal(list)  # List of detections for preview
    error = Signal(str)
    
    def __init__(self, frame: np.ndarray, params: DetectionParams, 
                 drum_center: tuple, drum_radius: int):
        super().__init__()
        self.frame = frame.copy() if frame is not None else None
        self.params = params
        self.drum_center = drum_center
        self.drum_radius = drum_radius
    
    def run(self):
        """Run detection on single frame."""
        try:
            if self.frame is None:
                self.finished.emit([])
                return
            
            detections = self._detect_frame(self.frame)
            self.finished.emit(detections)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _detect_frame(self, frame: np.ndarray) -> List[dict]:
        """Run detection pipeline on a single frame."""
        # Convert to grayscale
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        # Apply blur
        kernel = self.params.blur_kernel
        if kernel > 0 and kernel % 2 == 1:
            gray = cv2.GaussianBlur(gray, (kernel, kernel), 0)
        
        # Apply ROI mask (only detect inside drum)
        if self.drum_center and self.drum_radius > 0:
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.circle(mask, self.drum_center, self.drum_radius, 255, -1)
            gray = cv2.bitwise_and(gray, mask)
        
        # Run HoughCircles
        # param1 is the Canny high threshold (low is automatically half)
        # Use canny_high from UI if set, otherwise fall back to hough_param1
        canny_threshold = getattr(self.params, 'canny_high', self.params.hough_param1)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=self.params.hough_dp,
            minDist=self.params.hough_min_dist,
            param1=canny_threshold,
            param2=self.params.hough_param2,
            minRadius=self.params.min_radius_px,
            maxRadius=self.params.max_radius_px
        )
        
        detections = []
        if circles is not None:
            for circle in circles[0]:
                x, y, r = circle
                # Basic confidence based on radius consistency
                conf = 0.5 + 0.5 * (1.0 - abs(r - 20) / 30)
                conf = max(0.0, min(1.0, conf))
                
                detections.append({
                    "x": int(x),
                    "y": int(y),
                    "r_px": float(r),
                    "conf": round(conf, 3),
                    "cls": "unknown",  # Classification happens later
                    "is_preview": True
                })
        
        return detections


class BatchWorker(QObject):
    """
    Worker for full batch detection on all frames.
    Runs in background thread, emits progress updates.
    """
    
    progress = Signal(int, str)  # percent, message
    frame_done = Signal(int, list)  # frame_index, detections
    finished = Signal(dict)  # Full cache data
    error = Signal(str)
    cancelled = Signal()
    
    def __init__(self, video_path: str, params: DetectionParams,
                 drum_center: tuple, drum_radius: int,
                 frame_step: int = 1):
        super().__init__()
        self.video_path = video_path
        self.params = params
        self.drum_center = drum_center
        self.drum_radius = drum_radius
        self.frame_step = frame_step
        self._cancelled = False
    
    def cancel(self):
        """Request cancellation."""
        self._cancelled = True
    
    def run(self):
        """Run detection on all frames."""
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error.emit(f"Cannot open video: {self.video_path}")
                return
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            all_detections = {}
            processed = 0
            
            frame_idx = 0
            while frame_idx < total_frames:
                if self._cancelled:
                    cap.release()
                    self.cancelled.emit()
                    return
                
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if not ret:
                    frame_idx += self.frame_step
                    continue
                
                # Run detection
                detections = self._detect_frame(frame)
                all_detections[str(frame_idx)] = {
                    "detections": detections
                }
                
                self.frame_done.emit(frame_idx, detections)
                
                processed += 1
                percent = int((frame_idx / total_frames) * 100)
                self.progress.emit(percent, f"Frame {frame_idx}/{total_frames}")
                
                frame_idx += self.frame_step
            
            cap.release()
            
            # Build cache structure
            cache_data = {
                "metadata": {
                    "video_path": self.video_path,
                    "total_frames": total_frames,
                    "fps": fps,
                    "width": width,
                    "height": height,
                    "drum_center": list(self.drum_center) if self.drum_center else [0, 0],
                    "drum_radius": self.drum_radius,
                    "params_used": self.params.to_dict(),
                    "processed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
                "frames": all_detections
            }
            
            self.progress.emit(100, "Complete")
            self.finished.emit(cache_data)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _detect_frame(self, frame: np.ndarray) -> List[dict]:
        """Run detection pipeline on a single frame."""
        # Same as PreviewWorker
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame
        
        kernel = self.params.blur_kernel
        if kernel > 0 and kernel % 2 == 1:
            gray = cv2.GaussianBlur(gray, (kernel, kernel), 0)
        
        if self.drum_center and self.drum_radius > 0:
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.circle(mask, self.drum_center, self.drum_radius, 255, -1)
            gray = cv2.bitwise_and(gray, mask)
        
        # param1 is the Canny high threshold (low is automatically half)
        canny_threshold = getattr(self.params, 'canny_high', self.params.hough_param1)
        circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=self.params.hough_dp,
            minDist=self.params.hough_min_dist,
            param1=canny_threshold,
            param2=self.params.hough_param2,
            minRadius=self.params.min_radius_px,
            maxRadius=self.params.max_radius_px
        )
        
        detections = []
        if circles is not None:
            for circle in circles[0]:
                x, y, r = circle
                conf = 0.5 + 0.5 * (1.0 - abs(r - 20) / 30)
                conf = max(0.0, min(1.0, conf))
                
                detections.append({
                    "x": int(x),
                    "y": int(y),
                    "r_px": float(r),
                    "conf": round(conf, 3),
                    "cls": "unknown"
                })
        
        return detections


class DetectionController(QObject):
    """
    Controller for managing detection workers.
    Handles preview debouncing and batch job management.
    """
    
    preview_ready = Signal(list)  # Preview detections
    batch_progress = Signal(int, str)  # Percent, message
    batch_finished = Signal(dict)  # Cache data
    batch_cancelled = Signal()
    error = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.timeout.connect(self._run_preview)
        
        self._pending_preview = None
        self._preview_thread: Optional[QThread] = None
        self._preview_worker: Optional[PreviewWorker] = None
        self._batch_thread: Optional[QThread] = None
        self._batch_worker: Optional[BatchWorker] = None
        
        # Debounce delay (ms)
        self.preview_debounce_ms = 200
    
    def request_preview(self, frame: np.ndarray, params: DetectionParams,
                        drum_center: tuple, drum_radius: int):
        """
        Request a preview detection (debounced).
        Multiple rapid calls will only trigger one detection.
        """
        self._pending_preview = (frame, params, drum_center, drum_radius)
        self._preview_timer.start(self.preview_debounce_ms)
    
    def _run_preview(self):
        """Execute the pending preview."""
        if self._pending_preview is None:
            return
        
        frame, params, drum_center, drum_radius = self._pending_preview
        self._pending_preview = None
        
        # Cancel any running preview
        if self._preview_thread is not None and self._preview_thread.isRunning():
            self._preview_thread.quit()
            self._preview_thread.wait(500)
        
        # Create worker and thread
        self._preview_thread = QThread()
        # Store worker as instance variable to prevent garbage collection
        self._preview_worker = PreviewWorker(frame, params, drum_center, drum_radius)
        self._preview_worker.moveToThread(self._preview_thread)
        
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.finished.connect(self.preview_ready.emit)
        self._preview_worker.finished.connect(self._preview_thread.quit)
        self._preview_worker.error.connect(self.error.emit)
        self._preview_worker.error.connect(self._preview_thread.quit)
        
        self._preview_thread.start()
    
    def start_batch(self, video_path: str, params: DetectionParams,
                    drum_center: tuple, drum_radius: int,
                    frame_step: int = 1):
        """Start batch detection on all frames."""
        if self._batch_thread is not None and self._batch_thread.isRunning():
            self.error.emit("Batch detection already running")
            return
        
        self._batch_thread = QThread()
        self._batch_worker = BatchWorker(
            video_path, params, drum_center, drum_radius, frame_step
        )
        self._batch_worker.moveToThread(self._batch_thread)
        
        self._batch_thread.started.connect(self._batch_worker.run)
        self._batch_worker.progress.connect(self.batch_progress.emit)
        self._batch_worker.finished.connect(self._on_batch_finished)
        self._batch_worker.cancelled.connect(self._on_batch_cancelled)
        self._batch_worker.error.connect(self.error.emit)
        
        self._batch_thread.start()
    
    def cancel_batch(self):
        """Cancel running batch detection."""
        if self._batch_worker is not None:
            self._batch_worker.cancel()
    
    def _on_batch_finished(self, cache_data: dict):
        """Handle batch completion."""
        self.batch_finished.emit(cache_data)
        if self._batch_thread:
            self._batch_thread.quit()
            self._batch_thread.wait(1000)
    
    def _on_batch_cancelled(self):
        """Handle batch cancellation."""
        self.batch_cancelled.emit()
        if self._batch_thread:
            self._batch_thread.quit()
            self._batch_thread.wait(1000)
    
    @property
    def is_batch_running(self) -> bool:
        return self._batch_thread is not None and self._batch_thread.isRunning()
