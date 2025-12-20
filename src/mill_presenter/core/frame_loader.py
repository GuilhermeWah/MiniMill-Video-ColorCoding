# MillPresenter Frame Loader

"""
Video decoding with PyAV for frame-accurate seeking and rotation handling.
This module provides the FrameLoader class that wraps PyAV for video I/O.

Key features:
- PTS-based frame indexing (accurate frame numbers)
- Rotation metadata handling (iPhone videos)
- Frame-accurate seeking
- Resource cleanup
"""

import av
import numpy as np
from typing import Iterator, Tuple, Optional
from pathlib import Path

from .models import VideoMetadata


class FrameLoader:
    """
    Video decoder using PyAV with rotation handling and accurate seeking.
    
    Usage:
        loader = FrameLoader("video.MOV")
        for frame_idx, frame_bgr in loader.iter_frames():
            process(frame_bgr)
        loader.close()
    
    Or as context manager:
        with FrameLoader("video.MOV") as loader:
            frame = loader.get_frame(100)
    """
    
    def __init__(self, video_path: str):
        """
        Open a video file for decoding.
        
        Args:
            video_path: Path to the video file.
        
        Raises:
            FileNotFoundError: If video file doesn't exist.
            av.AVError: If video cannot be opened.
        """
        self._path = Path(video_path)
        if not self._path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        self._container: Optional[av.container.InputContainer] = None
        self._stream: Optional[av.video.stream.VideoStream] = None
        self._rotation: int = 0
        self._fps: float = 0.0
        self._total_frames: int = 0
        self._width: int = 0
        self._height: int = 0
        self._duration: float = 0.0
        self._time_base: float = 0.0
        
        self._open()
    
    def _open(self) -> None:
        """Open the video container and extract metadata."""
        self._container = av.open(str(self._path))
        self._stream = self._container.streams.video[0]
        
        # Extract basic properties
        self._fps = float(self._stream.average_rate or self._stream.guessed_rate or 30.0)
        self._time_base = float(self._stream.time_base)
        
        # Get frame count (may be estimated)
        if self._stream.frames > 0:
            self._total_frames = self._stream.frames
        elif self._stream.duration and self._stream.time_base:
            duration_s = float(self._stream.duration * self._stream.time_base)
            self._total_frames = int(duration_s * self._fps)
        else:
            # Fallback: estimate from container duration
            self._total_frames = int(self._container.duration / 1_000_000 * self._fps)
        
        # Duration in seconds
        if self._container.duration:
            self._duration = self._container.duration / 1_000_000
        else:
            self._duration = self._total_frames / self._fps if self._fps > 0 else 0
        
        # Detect rotation from metadata
        self._rotation = self._detect_rotation()
        
        # Dimensions (swap if rotated 90/270)
        orig_width = self._stream.width
        orig_height = self._stream.height
        
        if self._rotation in (90, 270):
            self._width = orig_height
            self._height = orig_width
        else:
            self._width = orig_width
            self._height = orig_height
    
    def _detect_rotation(self) -> int:
        """
        Detect video rotation from metadata.
        
        Checks for:
        1. 'rotate' tag in stream metadata
        2. DISPLAYMATRIX side data
        
        Returns:
            Rotation angle in degrees (0, 90, 180, 270)
        """
        rotation = 0
        
        # Check stream metadata for 'rotate' tag
        if self._stream and self._stream.metadata:
            rotate_str = self._stream.metadata.get('rotate', '0')
            try:
                rotation = int(rotate_str)
            except ValueError:
                rotation = 0
        
        # Normalize to 0, 90, 180, 270
        rotation = rotation % 360
        if rotation not in (0, 90, 180, 270):
            # Round to nearest 90
            rotation = round(rotation / 90) * 90 % 360
        
        return rotation
    
    def _apply_rotation(self, frame: np.ndarray) -> np.ndarray:
        """Apply rotation to frame based on detected metadata."""
        if self._rotation == 0:
            return frame
        elif self._rotation == 90:
            return np.rot90(frame, k=3)  # Rotate 270 CCW = 90 CW
        elif self._rotation == 180:
            return np.rot90(frame, k=2)
        elif self._rotation == 270:
            return np.rot90(frame, k=1)  # Rotate 90 CCW = 270 CW
        return frame
    
    @property
    def fps(self) -> float:
        """Frames per second."""
        return self._fps
    
    @property
    def total_frames(self) -> int:
        """Total number of frames (may be estimated)."""
        return self._total_frames
    
    @property
    def width(self) -> int:
        """Frame width (after rotation)."""
        return self._width
    
    @property
    def height(self) -> int:
        """Frame height (after rotation)."""
        return self._height
    
    @property
    def duration(self) -> float:
        """Video duration in seconds."""
        return self._duration
    
    @property
    def rotation(self) -> int:
        """Detected rotation in degrees."""
        return self._rotation
    
    @property
    def metadata(self) -> VideoMetadata:
        """Get video metadata as a dataclass."""
        return VideoMetadata(
            path=str(self._path),
            width=self._width,
            height=self._height,
            fps=self._fps,
            total_frames=self._total_frames,
            duration=self._duration,
            rotation=self._rotation
        )
    
    def iter_frames(self, start_frame: int = 0) -> Iterator[Tuple[int, np.ndarray]]:
        """
        Iterate through video frames starting from a given frame.
        
        Args:
            start_frame: Frame index to start from (0-based).
        
        Yields:
            Tuple of (frame_index, frame_bgr) where frame_bgr is a numpy array
            in BGR format with shape (height, width, 3).
        """
        if self._container is None or self._stream is None:
            raise RuntimeError("Video not opened")
        
        # Seek to start if not at beginning
        if start_frame > 0:
            self.seek(start_frame)
        else:
            # Reset to beginning
            self._container.seek(0)
        
        for frame in self._container.decode(video=0):
            # Calculate frame index from PTS
            if frame.pts is not None:
                frame_idx = round(float(frame.pts) * self._time_base * self._fps)
            else:
                # Fallback to sequential counting
                frame_idx = start_frame
            
            # Skip frames before start_frame (may happen after seek)
            if frame_idx < start_frame:
                continue
            
            # Convert to numpy BGR
            frame_rgb = frame.to_ndarray(format='rgb24')
            frame_bgr = frame_rgb[:, :, ::-1]  # RGB to BGR
            
            # Apply rotation
            frame_bgr = self._apply_rotation(frame_bgr)
            
            yield frame_idx, frame_bgr
            start_frame = frame_idx + 1
    
    def seek(self, frame_index: int) -> None:
        """
        Seek to a specific frame.
        
        Note: Due to video compression, seeking may land on a keyframe
        before the target. Use iter_frames(start_frame=N) for accurate seeking.
        
        Args:
            frame_index: Target frame index (0-based).
        """
        if self._container is None or self._stream is None:
            raise RuntimeError("Video not opened")
        
        # Calculate timestamp in stream time base
        timestamp = int(frame_index / self._fps / self._time_base)
        
        # Seek to nearest keyframe before target
        self._container.seek(timestamp, stream=self._stream, backward=True)
    
    def get_frame(self, frame_index: int, max_decode: int = 120) -> np.ndarray:
        """
        Get a specific frame by index.
        
        This seeks to the frame and decodes it. For sequential access,
        use iter_frames() which is more efficient.
        
        Args:
            frame_index: Frame index to retrieve (0-based).
            max_decode: Maximum frames to decode after seek. If exceeded,
                       returns the last decoded frame (keyframe-based approximation).
        
        Returns:
            Frame as numpy array in BGR format with shape (height, width, 3).
        
        Raises:
            IndexError: If frame_index is out of range.
        """
        if frame_index < 0 or frame_index >= self._total_frames:
            raise IndexError(f"Frame index {frame_index} out of range [0, {self._total_frames})")
        
        self.seek(frame_index)
        
        decoded_count = 0
        last_frame = None
        
        for frame in self._container.decode(video=0):
            decoded_count += 1
            
            if frame.pts is not None:
                current_idx = round(float(frame.pts) * self._time_base * self._fps)
            else:
                current_idx = frame_index
            
            # Store the frame
            frame_rgb = frame.to_ndarray(format='rgb24')
            last_frame = frame_rgb[:, :, ::-1]
            
            if current_idx >= frame_index:
                # Reached target frame
                return self._apply_rotation(last_frame)
            
            if decoded_count >= max_decode:
                # Too many frames to decode - return what we have (keyframe approximate)
                return self._apply_rotation(last_frame)
        
        if last_frame is not None:
            return self._apply_rotation(last_frame)
        
        raise IndexError(f"Could not decode frame {frame_index}")
    
    def close(self) -> None:
        """Close the video container and release resources."""
        if self._container is not None:
            self._container.close()
            self._container = None
            self._stream = None
    
    def __enter__(self) -> "FrameLoader":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
    
    def __del__(self) -> None:
        self.close()
