"""Generate calibration overlay images with 20cm (200mm) drum diameter."""
import cv2
import numpy as np
import os
from pathlib import Path

# Use pathlib to handle unicode paths properly
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "golden_frames"
OUTPUT_DIR = BASE_DIR / "output" / "calibration_test"

print('=== BEAD DETECTION WITH 20cm (200mm) DRUM CALIBRATION ===')
print()

drum_data = {
    'IMG_6535': {'cx': 1815, 'cy': 1074, 'r': 872},
    'IMG_1276': {'cx': 590, 'cy': 395, 'r': 365},
    'DSC_3310': {'cx': 967, 'cy': 551, 'r': 496},
}

def get_expected_radii(drum_r_px):
    """Calculate expected bead radii based on 200mm drum diameter."""
    px_per_mm = (drum_r_px * 2) / 200  # 200mm diameter
    return {
        '4mm': 3.94/2 * px_per_mm,
        '6mm': 5.79/2 * px_per_mm,
        '8mm': 7.63/2 * px_per_mm,
        '10mm': 9.90/2 * px_per_mm,
        'px_per_mm': px_per_mm
    }

# Color map for size classes (BGR)
colors = {
    '4mm': (255, 100, 100),   # Light blue
    '6mm': (100, 255, 100),   # Green
    '8mm': (100, 100, 255),   # Red
    '10mm': (255, 255, 100),  # Cyan
    'other': (128, 128, 128), # Gray
}

def imread_unicode(path: Path) -> np.ndarray:
    """Read image with unicode path support."""
    with open(path, 'rb') as f:
        data = np.frombuffer(f.read(), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def imwrite_unicode(path: Path, img: np.ndarray) -> bool:
    """Write image with unicode path support."""
    ext = path.suffix
    success, data = cv2.imencode(ext, img)
    if success:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(data.tobytes())
        return True
    return False

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

samples = ['IMG_6535', 'IMG_1276', 'DSC_3310']

for name in samples:
    path = DATA_DIR / f"{name}_frame_100.png"
    
    img = imread_unicode(path)
    if img is None:
        print(f'{name}: Failed to load from {path}')
        continue
    
    h, w = img.shape[:2]
    drum = drum_data[name]
    exp = get_expected_radii(drum['r'])
    px_mm = exp['px_per_mm']
    
    cx, cy, dr = drum['cx'], drum['cy'], drum['r']
    print(f'{name}:')
    print(f'  Resolution: {w}x{h}')
    print(f'  Drum: center=({cx}, {cy}), radius={dr}px')
    print(f'  px_per_mm: {px_mm:.2f}')
    
    # Create ROI mask (95% of drum radius to exclude rim)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (cx, cy), int(dr * 0.95), 255, -1)
    
    # Apply mask
    masked = cv2.bitwise_and(img, img, mask=mask)
    gray = cv2.cvtColor(masked, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 5)
    
    # Radius range based on calibration
    min_r = max(3, int(exp['4mm'] * 0.7))
    max_r = int(exp['10mm'] * 1.5)
    min_dist = int(exp['4mm'] * 1.5)
    
    print(f'  Detection params: r={min_r}-{max_r}px, minDist={min_dist}px')
    
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1, 
                               minDist=min_dist, param1=50, param2=30, 
                               minRadius=min_r, maxRadius=max_r)
    
    # Create overlay
    overlay = img.copy()
    
    # Draw drum boundary (faint gray)
    cv2.circle(overlay, (cx, cy), dr, (100, 100, 100), 2)
    
    stats = {'4mm': 0, '6mm': 0, '8mm': 0, '10mm': 0, 'other': 0}
    
    if circles is not None:
        for c in circles[0]:
            x, y, r = int(c[0]), int(c[1]), c[2]
            d_mm = (r * 2) / px_mm  # Convert to diameter in mm
            
            # Classify by size
            if 3.0 <= d_mm < 4.9:
                cls = '4mm'
            elif 4.9 <= d_mm < 6.7:
                cls = '6mm'
            elif 6.7 <= d_mm < 8.8:
                cls = '8mm'
            elif 8.8 <= d_mm < 12.0:
                cls = '10mm'
            else:
                cls = 'other'
            
            stats[cls] += 1
            color = colors[cls]
            cv2.circle(overlay, (x, y), int(r), color, 2)
            cv2.circle(overlay, (x, y), 2, color, -1)
        
        total = len(circles[0])
        print(f'  Detected: {total} circles')
        print('  Size distribution:')
        for cls, cnt in stats.items():
            pct = cnt / total * 100 if total > 0 else 0
            print(f'    {cls}: {cnt} ({pct:.0f}%)')
    else:
        print('  No circles detected!')
    
    # Add legend
    y_off = 30
    for cls, color in colors.items():
        cv2.rectangle(overlay, (10, y_off-15), (30, y_off+5), color, -1)
        cv2.putText(overlay, cls, (40, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_off += 30
    
    # Add calibration info at bottom
    txt = f'Drum: 200mm | px/mm: {px_mm:.2f}'
    cv2.putText(overlay, txt, (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Save
    out_path = OUTPUT_DIR / f'{name}_20cm_calibration.png'
    imwrite_unicode(out_path, overlay)
    print(f'  Saved: {out_path}')
    print()

print('Done! Check output/calibration_test/ for images.')
