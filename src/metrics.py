"""
Quality metrics module for MillPresenter pipeline.

STEP_08: Quality Metrics

This module computes quality metrics for pipeline validation:
1. Count Stability - coefficient of variation across frames
2. Size Distribution Stability - class proportion consistency
3. Confidence Behavior - distribution analysis
4. Throughput - processing time tracking

These metrics validate that the pipeline produces stable, trustworthy results.
"""

import math
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import statistics


@dataclass
class FrameMetrics:
    """Metrics for a single frame."""
    video: str
    frame_idx: int
    total_count: int
    counts_by_class: Dict[str, int]
    confidence_values: List[float]
    processing_time_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "video": self.video,
            "frame_idx": self.frame_idx,
            "total_count": self.total_count,
            "counts_by_class": self.counts_by_class,
            "confidence_stats": {
                "min": round(min(self.confidence_values), 3) if self.confidence_values else 0,
                "max": round(max(self.confidence_values), 3) if self.confidence_values else 0,
                "mean": round(statistics.mean(self.confidence_values), 3) if self.confidence_values else 0,
                "median": round(statistics.median(self.confidence_values), 3) if self.confidence_values else 0,
                "stdev": round(statistics.stdev(self.confidence_values), 3) if len(self.confidence_values) > 1 else 0,
            },
            "processing_time_ms": round(self.processing_time_ms, 2)
        }


@dataclass
class CountStabilityMetrics:
    """Count stability across frames."""
    frame_counts: List[int]
    mean_count: float
    std_count: float
    cv: float  # Coefficient of variation
    min_count: int
    max_count: int
    
    def to_dict(self) -> dict:
        return {
            "n_frames": len(self.frame_counts),
            "mean_count": round(self.mean_count, 2),
            "std_count": round(self.std_count, 2),
            "cv": round(self.cv, 3),  # Lower is better
            "min_count": self.min_count,
            "max_count": self.max_count,
            "range": self.max_count - self.min_count,
            "stability_rating": self._get_rating()
        }
    
    def _get_rating(self) -> str:
        """Rate stability based on CV."""
        if self.cv < 0.10:
            return "Excellent"
        elif self.cv < 0.20:
            return "Good"
        elif self.cv < 0.35:
            return "Acceptable"
        else:
            return "Poor"


@dataclass
class SizeDistributionMetrics:
    """Size distribution stability across frames."""
    class_proportions: Dict[str, List[float]]  # class -> list of proportions per frame
    mean_proportions: Dict[str, float]
    std_proportions: Dict[str, float]
    
    def to_dict(self) -> dict:
        result = {
            "mean_proportions": {k: round(v * 100, 1) for k, v in self.mean_proportions.items()},
            "std_proportions": {k: round(v * 100, 1) for k, v in self.std_proportions.items()},
            "stability_by_class": {}
        }
        
        for cls in self.mean_proportions:
            mean = self.mean_proportions[cls]
            std = self.std_proportions[cls]
            cv = std / mean if mean > 0 else 0
            result["stability_by_class"][cls] = {
                "cv": round(cv, 3),
                "rating": self._rate_cv(cv)
            }
        
        return result
    
    def _rate_cv(self, cv: float) -> str:
        if cv < 0.15:
            return "Stable"
        elif cv < 0.30:
            return "Moderate"
        else:
            return "Variable"


@dataclass
class ConfidenceMetrics:
    """Confidence distribution analysis."""
    all_confidences: List[float]
    histogram: Dict[str, int]  # bin -> count
    mean: float
    median: float
    std: float
    min_val: float
    max_val: float
    
    def to_dict(self) -> dict:
        return {
            "n_detections": len(self.all_confidences),
            "mean": round(self.mean, 3),
            "median": round(self.median, 3),
            "std": round(self.std, 3),
            "min": round(self.min_val, 3),
            "max": round(self.max_val, 3),
            "range": round(self.max_val - self.min_val, 3),
            "histogram": self.histogram,
            "distribution_rating": self._get_rating()
        }
    
    def _get_rating(self) -> str:
        """Check if confidence is well-distributed (not collapsed)."""
        range_val = self.max_val - self.min_val
        if range_val < 0.2:
            return "Collapsed (bad)"
        elif self.std < 0.05:
            return "Narrow (check)"
        elif self.std > 0.25:
            return "Wide (good separation)"
        else:
            return "Normal"


@dataclass
class QualityReport:
    """Complete quality metrics report."""
    video_name: str
    n_frames: int
    total_detections: int
    count_stability: CountStabilityMetrics
    size_distribution: SizeDistributionMetrics
    confidence: ConfidenceMetrics
    throughput_fps: float
    frame_metrics: List[FrameMetrics]
    
    def to_dict(self) -> dict:
        return {
            "summary": {
                "video": self.video_name,
                "n_frames": self.n_frames,
                "total_detections": self.total_detections,
                "throughput_fps": round(self.throughput_fps, 2)
            },
            "count_stability": self.count_stability.to_dict(),
            "size_distribution": self.size_distribution.to_dict(),
            "confidence": self.confidence.to_dict(),
            "per_frame": [f.to_dict() for f in self.frame_metrics]
        }


def compute_count_stability(frame_metrics: List[FrameMetrics]) -> CountStabilityMetrics:
    """Compute count stability metrics."""
    counts = [f.total_count for f in frame_metrics]
    
    if not counts:
        return CountStabilityMetrics([], 0, 0, 0, 0, 0)
    
    mean_count = statistics.mean(counts)
    std_count = statistics.stdev(counts) if len(counts) > 1 else 0
    cv = std_count / mean_count if mean_count > 0 else 0
    
    return CountStabilityMetrics(
        frame_counts=counts,
        mean_count=mean_count,
        std_count=std_count,
        cv=cv,
        min_count=min(counts),
        max_count=max(counts)
    )


def compute_size_distribution(frame_metrics: List[FrameMetrics]) -> SizeDistributionMetrics:
    """Compute size distribution stability."""
    classes = ["4mm", "6mm", "8mm", "10mm", "unknown"]
    class_proportions = {cls: [] for cls in classes}
    
    for f in frame_metrics:
        total = f.total_count
        if total == 0:
            continue
        for cls in classes:
            count = f.counts_by_class.get(cls, 0)
            proportion = count / total
            class_proportions[cls].append(proportion)
    
    mean_props = {}
    std_props = {}
    
    for cls in classes:
        props = class_proportions[cls]
        if props:
            mean_props[cls] = statistics.mean(props)
            std_props[cls] = statistics.stdev(props) if len(props) > 1 else 0
        else:
            mean_props[cls] = 0
            std_props[cls] = 0
    
    return SizeDistributionMetrics(
        class_proportions=class_proportions,
        mean_proportions=mean_props,
        std_proportions=std_props
    )


def compute_confidence_metrics(frame_metrics: List[FrameMetrics]) -> ConfidenceMetrics:
    """Compute confidence distribution metrics."""
    all_conf = []
    for f in frame_metrics:
        all_conf.extend(f.confidence_values)
    
    if not all_conf:
        return ConfidenceMetrics([], {}, 0, 0, 0, 0, 0)
    
    # Build histogram
    bins = ["0.5-0.6", "0.6-0.7", "0.7-0.8", "0.8-0.9", "0.9-1.0"]
    histogram = {b: 0 for b in bins}
    
    for c in all_conf:
        if c < 0.6:
            histogram["0.5-0.6"] += 1
        elif c < 0.7:
            histogram["0.6-0.7"] += 1
        elif c < 0.8:
            histogram["0.7-0.8"] += 1
        elif c < 0.9:
            histogram["0.8-0.9"] += 1
        else:
            histogram["0.9-1.0"] += 1
    
    return ConfidenceMetrics(
        all_confidences=all_conf,
        histogram=histogram,
        mean=statistics.mean(all_conf),
        median=statistics.median(all_conf),
        std=statistics.stdev(all_conf) if len(all_conf) > 1 else 0,
        min_val=min(all_conf),
        max_val=max(all_conf)
    )


def generate_quality_report(
    video_name: str,
    frame_metrics: List[FrameMetrics],
    total_processing_time_s: float = 0
) -> QualityReport:
    """Generate complete quality report for a video."""
    
    total_detections = sum(f.total_count for f in frame_metrics)
    n_frames = len(frame_metrics)
    
    count_stability = compute_count_stability(frame_metrics)
    size_distribution = compute_size_distribution(frame_metrics)
    confidence = compute_confidence_metrics(frame_metrics)
    
    throughput = n_frames / total_processing_time_s if total_processing_time_s > 0 else 0
    
    return QualityReport(
        video_name=video_name,
        n_frames=n_frames,
        total_detections=total_detections,
        count_stability=count_stability,
        size_distribution=size_distribution,
        confidence=confidence,
        throughput_fps=throughput,
        frame_metrics=frame_metrics
    )


def generate_aggregate_report(reports: List[QualityReport]) -> dict:
    """Generate aggregate report across multiple videos."""
    
    total_frames = sum(r.n_frames for r in reports)
    total_detections = sum(r.total_detections for r in reports)
    
    # Aggregate count stability
    all_counts = []
    for r in reports:
        all_counts.extend(r.count_stability.frame_counts)
    
    overall_cv = 0
    if all_counts:
        mean = statistics.mean(all_counts)
        std = statistics.stdev(all_counts) if len(all_counts) > 1 else 0
        overall_cv = std / mean if mean > 0 else 0
    
    # Aggregate size distribution
    all_frame_metrics = []
    for r in reports:
        all_frame_metrics.extend(r.frame_metrics)
    
    overall_size = compute_size_distribution(all_frame_metrics)
    overall_conf = compute_confidence_metrics(all_frame_metrics)
    
    return {
        "aggregate_summary": {
            "total_videos": len(reports),
            "total_frames": total_frames,
            "total_detections": total_detections,
            "overall_count_cv": round(overall_cv, 3),
            "count_stability_rating": _rate_cv(overall_cv)
        },
        "size_distribution": overall_size.to_dict(),
        "confidence": overall_conf.to_dict(),
        "per_video": [r.to_dict()["summary"] for r in reports]
    }


def _rate_cv(cv: float) -> str:
    if cv < 0.10:
        return "Excellent"
    elif cv < 0.20:
        return "Good"
    elif cv < 0.35:
        return "Acceptable"
    else:
        return "Poor"
