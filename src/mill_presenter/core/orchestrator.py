# MillPresenter Processor Orchestrator

"""
Pipeline coordinator that ties together all detection components.
Runs the full offline detection pipeline from video to cache.

Legacy nomenclature: ProcessorOrchestrator
"""

from typing import Callable, Optional, Dict, Any
import time

from mill_presenter.core.frame_loader import FrameLoader
from mill_presenter.core.drum_geometry import DrumGeometry
from mill_presenter.core.preprocessor import Preprocessor
from mill_presenter.core.vision_processor import VisionProcessor
from mill_presenter.core.confidence_scorer import ConfidenceScorer
from mill_presenter.core.detection_filter import DetectionFilter
from mill_presenter.core.classifier import Classifier
from mill_presenter.core.results_cache import ResultsCache
from mill_presenter.core.models import FrameDetections
from mill_presenter.utils import config


class ProcessorOrchestrator:
    """
    Coordinates the full offline detection pipeline.
    
    Pipeline flow:
    1. Load video (FrameLoader)
    2. Detect drum geometry (DrumGeometry)
    3. For each frame:
       a. Preprocess (Preprocessor)
       b. Detect circles (VisionProcessor)
       c. Score detections (ConfidenceScorer)
       d. Filter detections (DetectionFilter)
       e. Classify (Classifier)
       f. Cache results (ResultsCache)
    4. Finalize cache
    """
    
    def __init__(self, 
                 video_path: str,
                 cache_path: str,
                 drum_diameter_mm: float = 200.0,
                 cfg: Optional[Dict[str, Any]] = None):
        """
        Initialize orchestrator.
        
        Args:
            video_path: Path to input video.
            cache_path: Path for output cache.
            drum_diameter_mm: Physical drum diameter for calibration.
            cfg: Optional config override.
        """
        self._video_path = video_path
        self._cache_path = cache_path
        self._drum_diameter_mm = drum_diameter_mm
        self._cfg = cfg or config.CONFIG
        
        self._cancelled = False
        self._geometry: Optional[DrumGeometry] = None
        self._effective_px_per_mm: float = 4.0  # Default fallback
        
        # Components (initialized lazily)
        self._loader: Optional[FrameLoader] = None
        self._preprocessor: Optional[Preprocessor] = None
        self._processor: Optional[VisionProcessor] = None
        self._scorer: Optional[ConfidenceScorer] = None
        self._filter: Optional[DetectionFilter] = None
        self._classifier: Optional[Classifier] = None
        self._cache: Optional[ResultsCache] = None
    
    def run(self, 
            progress_callback: Optional[Callable[[int, int], None]] = None,
            limit: Optional[int] = None) -> bool:
        """
        Run the full detection pipeline.
        
        Args:
            progress_callback: Called with (current_frame, total_frames).
            limit: Optional limit on number of frames to process.
            
        Returns:
            True if completed successfully.
        """
        self._cancelled = False
        start_time = time.time()
        
        try:
            # Initialize components
            self._init_components()
            
            # Get first frame for geometry detection
            first_frame = self._loader.get_frame(0)
            
            # Detect drum geometry
            print("Detecting drum geometry...")
            self._geometry = DrumGeometry.detect(first_frame, self._drum_diameter_mm)
            print(f"  Drum: center=({self._geometry.center}), r={self._geometry.radius}px")
            print(f"  Auto calibration: {self._geometry.px_per_mm:.3f} px/mm")
            
            # Check for manual calibration override
            manual_px_per_mm, cal_source = config.get_calibration()
            if manual_px_per_mm is not None:
                self._effective_px_per_mm = manual_px_per_mm
                print(f"  Manual calibration: {manual_px_per_mm:.3f} px/mm (USING THIS)")
            else:
                self._effective_px_per_mm = self._geometry.px_per_mm
                print(f"  Using auto calibration")
            
            # Setup cache
            total_frames = min(self._loader.total_frames, limit) if limit else self._loader.total_frames
            
            self._cache.start_processing(
                total_frames=total_frames,
                metadata=self._loader.metadata.to_dict(),
                cfg=self._cfg
            )
            
            # Generate ROI mask
            roi_mask = self._geometry.get_roi_mask(
                (self._loader.height, self._loader.width)
            )
            
            # Process frames
            processed_count = 0
            for frame_idx, frame_bgr in self._loader.iter_frames():
                if self._cancelled:
                    print("Processing cancelled.")
                    return False
                
                if limit and processed_count >= limit:
                    break
                
                # Pipeline stages
                detections = self._process_frame(frame_bgr, roi_mask, frame_idx)
                
                # Cache results
                timestamp = frame_idx / self._loader.fps
                self._cache.append_frame(FrameDetections(
                    frame_id=frame_idx,
                    timestamp=timestamp,
                    balls=detections
                ))
                
                processed_count += 1
                
                if progress_callback:
                    progress_callback(processed_count, total_frames)
            
            # Finalize
            self._cache.finalize()
            
            elapsed = time.time() - start_time
            print(f"Processing complete: {processed_count} frames in {elapsed:.1f}s")
            print(f"  Rate: {processed_count/elapsed:.1f} fps")
            
            return True
            
        except Exception as e:
            print(f"Processing failed: {e}")
            raise
        finally:
            self._cleanup()
    
    def _init_components(self) -> None:
        """Initialize all pipeline components."""
        self._loader = FrameLoader(self._video_path)
        self._preprocessor = Preprocessor(self._cfg)
        self._processor = VisionProcessor(self._cfg)
        self._scorer = ConfidenceScorer(self._cfg)
        self._filter = DetectionFilter(self._cfg)
        self._classifier = Classifier()
        self._cache = ResultsCache(self._cache_path)
    
    def _process_frame(self, frame_bgr, roi_mask, frame_idx):
        """Process a single frame through the pipeline."""
        # Stage 1: Preprocess
        preprocessed = self._preprocessor.process(frame_bgr, roi_mask)
        
        # Stage 2: Detect
        candidates = self._processor.detect(preprocessed, self._geometry)
        
        # Stage 3: Score
        scored = self._scorer.score(candidates, preprocessed, self._geometry)
        
        # Stage 4: Filter
        filtered = self._filter.filter(scored, self._geometry, preprocessed)
        
        # Stage 5: Classify
        balls = self._classifier.classify(filtered, self._effective_px_per_mm)
        
        return balls
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        if self._loader:
            self._loader.close()
            self._loader = None
    
    def cancel(self) -> None:
        """Cancel ongoing processing."""
        self._cancelled = True
    
    @property
    def geometry(self) -> Optional[DrumGeometry]:
        """Get detected drum geometry (available after run)."""
        return self._geometry
