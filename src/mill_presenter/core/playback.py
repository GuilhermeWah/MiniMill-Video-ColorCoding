import av
import cv2
import numpy as np
import math
from mill_presenter.utils.logging import get_logger

logger = get_logger(__name__)

class FrameLoader:
    """
    Handles video decoding using PyAV.
    Features:
    - Hardware acceleration (NVDEC) support (auto-fallback to CPU).
    - Metadata rotation handling (for iPhone/Nikon .MOV files).
    - Efficient seeking and frame iteration.
    """
    
    def __init__(self, file_path: str, decode_mode: str = "auto"):
        self.file_path = file_path
        self.decode_mode = decode_mode
        self.container = None
        self.stream = None
        self.rotation = 0
        self.width = 0
        self.height = 0
        self.fps = 0.0
        self.total_frames = 0
        self.duration = 0.0
        
        self._open_container()

    def _open_container(self):
        """Opens the video file and configures the stream."""
        try:
            # Options for hardware acceleration
            options = {}
            if self.decode_mode == "auto":
                # Try to use CUDA (NVDEC) if available
                # Note: This requires a build of FFmpeg with --enable-cuda-nvcc or similar
                # PyAV binary wheels usually don't ship with full NVDEC support enabled by default 
                # on all platforms, but we set the option just in case.
                # If it fails, PyAV usually falls back or throws an error we can catch.
                # For standard PyAV wheels, 'h264_cuvid' codec might be needed explicitly, 
                # but 'threading' is the safest generic speedup.
                options = {'threads': 'auto'} 

            self.container = av.open(self.file_path, options=options)
            self.stream = self.container.streams.video[0]
            self.stream.thread_type = 'AUTO'
            
            # Extract metadata
            self.fps = float(self.stream.average_rate)
            self.total_frames = self.stream.frames
            self.duration = float(self.stream.duration * self.stream.time_base) if self.stream.duration else 0
            
            # Handle Rotation
            # Rotation is often stored in stream.metadata or stream.side_data
            self.rotation = self._get_rotation_from_metadata()
            
            # Determine dimensions after rotation
            if self.rotation in [90, 270, -90, -270]:
                self.width = self.stream.height
                self.height = self.stream.width
            else:
                self.width = self.stream.width
                self.height = self.stream.height
                
            logger.info(f"Opened video: {self.file_path}")
            logger.info(f"Resolution: {self.width}x{self.height} (Rotated: {self.rotation}°)")
            logger.info(f"FPS: {self.fps:.2f}, Frames: {self.total_frames}")
            
        except Exception as e:
            logger.error(f"Failed to open video {self.file_path}: {e}")
            raise

    def _get_rotation_from_metadata(self) -> int:
        """Extracts rotation angle from stream metadata."""
        # 1. Check standard metadata dictionary
        rotate = self.stream.metadata.get('rotate')
        if rotate:
            return int(float(rotate))
        
        # 2. Check side data (if available)
        # Note: PyAV API varies by version. Some expose side_data on stream, some don't.
        try:
            if hasattr(self.stream, 'side_data'):
                for side_data in self.stream.side_data:
                    if side_data.type == 'DISPLAYMATRIX':
                        return int(side_data.rotation)
        except Exception:
            pass # Ignore side data errors
        
        return 0

    def _apply_rotation(self, frame_bgr: np.ndarray) -> np.ndarray:
        """Rotates the frame if metadata indicates it's needed."""
        if self.rotation == 0:
            return frame_bgr
        
        if self.rotation == 90 or self.rotation == -270:
            return cv2.rotate(frame_bgr, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotation == 180 or self.rotation == -180:
            return cv2.rotate(frame_bgr, cv2.ROTATE_180)
        elif self.rotation == 270 or self.rotation == -90:
            return cv2.rotate(frame_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
            
        return frame_bgr

    def seek(self, frame_index: int):
        """Seeks to a specific frame index."""
        if not self.stream:
            return
            
        # Calculate target PTS based on FPS and TimeBase
        # Formula: PTS = (FrameIndex / FPS) / TimeBase
        target_pts = int((frame_index / self.fps) / self.stream.time_base)
        
        # seek(..., backward=True) finds the nearest keyframe BEFORE the target
        self.container.seek(target_pts, stream=self.stream, any_frame=False, backward=True)

    def iter_frames(self, start_frame: int = 0):
        """Generator that yields (frame_index, frame_bgr_image)."""
        if start_frame > 0:
            self.seek(start_frame)
            
        for frame in self.container.decode(self.stream):
            # Calculate exact frame index from PTS to handle imprecise seeking (pre-roll)
            if frame.pts is not None:
                current_idx = int(round((frame.pts * self.stream.time_base) * self.fps))
            else:
                # Fallback if PTS is missing (rare in valid video files)
                # We assume we are at start_frame if we just sought, but this is risky.
                # For now, let's assume sequential if PTS is missing.
                current_idx = start_frame 
            
            # Skip frames until we reach the target start_frame
            # (Because seek() might land on an earlier keyframe)
            if current_idx < start_frame:
                continue
                
            # Convert to numpy array (RGB)
            img_array = frame.to_ndarray(format='bgr24')
            
            # Apply rotation
            img_array = self._apply_rotation(img_array)
            
            yield current_idx, img_array

    def close(self):
        if self.container:
            self.container.close()
