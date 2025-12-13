"""
Playback renderer module for MillPresenter pipeline.

STEP_09: Visualization & Playback

This module handles real-time overlay rendering for cached playback:
- Reads detection cache (no CV processing)
- Renders color-coded overlays at 30-60 FPS
- Supports filtering by confidence and class
- Displays statistics overlay
"""

import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from cache import CachedDetection, FrameCache


@dataclass
class PlaybackConfig:
    """Configuration for playback rendering."""
    # Class visibility
    show_4mm: bool = True
    show_6mm: bool = True
    show_8mm: bool = True
    show_10mm: bool = True
    show_unknown: bool = False
    
    # Confidence filter
    min_confidence: float = 0.0
    
    # Visual settings
    circle_thickness: int = 2
    overlay_opacity: float = 0.4
    show_center_dot: bool = True
    center_dot_radius: int = 2
    use_antialiasing: bool = True
    
    # Stats overlay
    show_stats: bool = True
    show_legend: bool = True
    
    # Colors (BGR)
    class_colors: Dict[str, Tuple[int, int, int]] = None
    
    def __post_init__(self):
        if self.class_colors is None:
            self.class_colors = {
                "4mm": (0, 0, 255),      # Red
                "6mm": (0, 255, 0),      # Green
                "8mm": (255, 0, 0),      # Blue
                "10mm": (0, 255, 255),   # Yellow
                "unknown": (128, 128, 128)  # Gray
            }
    
    def get_visible_classes(self) -> List[str]:
        """Get list of classes that should be shown."""
        classes = []
        if self.show_4mm:
            classes.append("4mm")
        if self.show_6mm:
            classes.append("6mm")
        if self.show_8mm:
            classes.append("8mm")
        if self.show_10mm:
            classes.append("10mm")
        if self.show_unknown:
            classes.append("unknown")
        return classes


class PlaybackRenderer:
    """Renders detection overlays for video playback."""
    
    def __init__(self, config: PlaybackConfig = None):
        self.config = config or PlaybackConfig()
    
    def render_frame(self, 
                     frame: np.ndarray,
                     detections: List[CachedDetection],
                     drum_center: Tuple[int, int] = None,
                     drum_radius: int = None,
                     stats: Dict[str, int] = None) -> np.ndarray:
        """
        Render overlay on a single frame.
        
        Args:
            frame: Original BGR frame
            detections: List of detections to draw
            drum_center: Optional drum center for ROI circle
            drum_radius: Optional drum radius for ROI circle
            stats: Optional stats dict for overlay
            
        Returns:
            Frame with overlay rendered
        """
        cfg = self.config
        
        # Create overlay layer
        overlay = frame.copy()
        
        # Draw drum ROI if provided
        if drum_center and drum_radius:
            cv2.circle(overlay, drum_center, drum_radius, (80, 80, 80), 1)
        
        # Filter detections
        visible_classes = cfg.get_visible_classes()
        filtered = [d for d in detections 
                   if d.cls in visible_classes and d.conf >= cfg.min_confidence]
        
        # Line type
        line_type = cv2.LINE_AA if cfg.use_antialiasing else cv2.LINE_8
        
        # Draw each detection
        for det in filtered:
            color = cfg.class_colors.get(det.cls, (128, 128, 128))
            center = (det.x, det.y)
            radius = int(det.r_px)
            
            # Draw circle
            cv2.circle(overlay, center, radius, color, cfg.circle_thickness, line_type)
            
            # Draw center dot
            if cfg.show_center_dot:
                cv2.circle(overlay, center, cfg.center_dot_radius, color, -1, line_type)
        
        # Blend overlay with original
        result = cv2.addWeighted(overlay, cfg.overlay_opacity, 
                                 frame, 1 - cfg.overlay_opacity, 0)
        
        # Draw stats overlay (not blended - on top)
        if cfg.show_stats and stats:
            result = self._draw_stats(result, stats, filtered)
        
        if cfg.show_legend:
            result = self._draw_legend(result)
        
        return result
    
    def _draw_stats(self, frame: np.ndarray, stats: Dict[str, int],
                    visible_detections: List[CachedDetection]) -> np.ndarray:
        """Draw statistics overlay."""
        h, w = frame.shape[:2]
        
        # Background box
        box_w, box_h = 180, 100
        x, y = w - box_w - 10, 10
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + box_w, y + box_h), (30, 30, 30), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        # Text
        visible_count = len(visible_detections)
        total_count = stats.get("total", 0)
        
        cv2.putText(frame, f"Detections: {visible_count}/{total_count}",
                   (x + 10, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # Per-class counts (visible only)
        class_counts = {}
        for det in visible_detections:
            class_counts[det.cls] = class_counts.get(det.cls, 0) + 1
        
        y_offset = 45
        for cls in ["4mm", "6mm", "8mm", "10mm"]:
            count = class_counts.get(cls, 0)
            color = self.config.class_colors.get(cls, (255, 255, 255))
            cv2.putText(frame, f"{cls}: {count}", (x + 10, y + y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            y_offset += 15
        
        return frame
    
    def _draw_legend(self, frame: np.ndarray) -> np.ndarray:
        """Draw color legend."""
        cfg = self.config
        h, w = frame.shape[:2]
        
        # Legend position (bottom-left)
        x, y = 10, h - 90
        
        # Semi-transparent background
        box_w, box_h = 100, 80
        overlay = frame.copy()
        cv2.rectangle(overlay, (x, y), (x + box_w, y + box_h), (30, 30, 30), -1)
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)
        
        # Draw legend items
        y_offset = 15
        for cls in ["4mm", "6mm", "8mm", "10mm"]:
            color = cfg.class_colors.get(cls, (128, 128, 128))
            visible = cls in cfg.get_visible_classes()
            
            # Color swatch
            swatch_y = y + y_offset
            cv2.rectangle(frame, (x + 5, swatch_y - 8), (x + 20, swatch_y + 2), color, -1)
            
            # Label
            label = f"{cls}" + (" ✓" if visible else "")
            text_color = (255, 255, 255) if visible else (100, 100, 100)
            cv2.putText(frame, label, (x + 25, swatch_y),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, text_color, 1)
            y_offset += 18
        
        return frame


def create_playback_config_from_size_config(size_config: Dict[str, Any]) -> PlaybackConfig:
    """Create PlaybackConfig from SIZE_CONFIG dict."""
    return PlaybackConfig(
        circle_thickness=size_config.get("circle_thickness", 2),
        overlay_opacity=size_config.get("overlay_opacity", 0.4),
        center_dot_radius=size_config.get("center_dot_radius", 2),
        use_antialiasing=size_config.get("use_antialiasing", True),
        class_colors=size_config.get("class_colors", None)
    )
