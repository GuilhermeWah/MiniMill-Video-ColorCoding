import argparse
import sys
import os
import yaml
import logging

# Ensure src is in path so we can import mill_presenter
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from mill_presenter.core.playback import FrameLoader
from mill_presenter.core.processor import VisionProcessor
from mill_presenter.core.cache import ResultsCache
from mill_presenter.core.orchestrator import ProcessorOrchestrator
from mill_presenter.utils.logging import setup_logging, get_logger

def main():
    parser = argparse.ArgumentParser(description="Run MillPresenter detection pipeline.")
    parser.add_argument("--input", required=True, help="Path to input video file")
    parser.add_argument("--output", required=True, help="Path to output .jsonl file")
    parser.add_argument("--config", required=True, help="Path to configuration .yaml file")
    parser.add_argument("--roi", help="Path to ROI mask image (optional)")
    
    args = parser.parse_args()
    
    setup_logging()
    logger = get_logger("CLI")
    
    # 1. Load Config
    if not os.path.exists(args.config):
        logger.error(f"Config file not found: {args.config}")
        sys.exit(1)
        
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
        
    # 2. Initialize Components
    try:
        logger.info(f"Opening video: {args.input}")
        loader = FrameLoader(args.input)
        
        logger.info("Initializing VisionProcessor...")
        processor = VisionProcessor(config)
        
        logger.info(f"Initializing ResultsCache: {args.output}")
        cache = ResultsCache(args.output)
        
        orchestrator = ProcessorOrchestrator(loader, processor, cache)
        
        # Load ROI if provided
        if args.roi:
            import cv2
            logger.info(f"Loading ROI mask: {args.roi}")
            roi_mask = cv2.imread(args.roi, cv2.IMREAD_GRAYSCALE)
            if roi_mask is None:
                logger.warning(f"Failed to load ROI mask from {args.roi}. Proceeding without it.")
            else:
                orchestrator.set_roi_mask(roi_mask)
        
        # 3. Run Pipeline
        def progress_cb(percent):
            # Simple progress bar
            bar_len = 20
            filled = int(bar_len * percent / 100)
            bar = '=' * filled + '-' * (bar_len - filled)
            sys.stdout.write(f'\rProgress: [{bar}] {percent:.1f}%')
            sys.stdout.flush()
            
        logger.info("Starting detection...")
        orchestrator.run(progress_callback=progress_cb)
        print() # Newline after progress bar
        logger.info("Detection completed successfully.")
        
    except Exception as e:
        logger.exception("An error occurred during execution.")
        sys.exit(1)

if __name__ == "__main__":
    main()
