 

COMP 4910 Computer Science Capstone Project Course – Video Mill Detection 

 

Zach Annett, Guilherme Falcao, Daniel Oloyede 

T00688845, T00660722, T00684580 

Supervisor: Dr. Musfiq Rahman 

Dec. 10th, 2025 

 

1.2 Abstract 

This project uses computer vision to detect beads of 4 specific sizes on an inputted video. The detection range is adjustable to fit the video, allowing for different video distances. This project is made to detect the different sized beads spinning inside of a specific spinning drum, which simulates how a mill processes ore.  

 

​​1.3 Table of Contents 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​ 

​​ 

1.4 Introduction 

This project presents MillPresenter, a desktop software application designed to support professional presentations of grinding mill operations through high-resolution video analysis and interactive visualization. The system processes 1080p video footage recorded at 60 frames per second and automatically detects and classifies grinding beads into four predefined diameter categories: 4 mm, 6 mm, 8 mm, and 10 mm. Using a dedicated computer vision pipeline tailored to industrial imaging conditions, the system delivers accurate measurements and visually interpretable overlays that enhance communication during client demonstrations. 

The primary objective of MillPresenter is to enable real-time toggling of bead size classifications during video playback without compromising smoothness or responsiveness. To achieve this, the application adopts an offline detection architecture in which computationally demanding analysis is completed in advance, and results are cached for instantaneous retrieval during presentations. This approach ensures that frame rate stability and user interaction are maintained at professional standards, even on standard Windows laptop hardware. 

The relevance of this project extends to applications and process optimization engineers who frequently analyze bead dynamics to explain mill performance characteristics. Conventional tools lack domain-specific features for bead classification and often cannot maintain high-quality playback during analysis. MillPresenter addresses these limitations through an optimized pipeline that balances computational efficiency with precision. 

This report proceeds as follows. Section 1.5 reviews literature and technological background; Section 1.6 articulates the problem being addressed; Section 1.7 describes the methodology and architectural design; Section 1.8 details the implementation; Section 1.9 presents results and analysis; Section 1.10 offers a discussion of findings and implications; and Section 1.11 concludes the report with reflections and contributions. 

1.5 Background and Literature Review 

1.5.1 Background 

Contextual information regarding this project may be required to understand some of our design decisions. There was a previous group who had worked with this project and solved it in a different manner. The previous group had created a solution where the different sized balls were all painted a different colour, and the detection was running based on the detected colour of the ball. For our project, the colours were removed from the balls, where they were left with a consistent metal sheen. The removal of the paint eliminated another potential variable in how the beads behave inside the simulation, making it more likely to be accurate. Our project aimed to detect the beads based on their size alone. We aimed our research towards Python development as it had plenty of research materials pertaining to object detection, and considering our current experience in this particular field we felt it was the best fit for our purposes. 

 

There were two major design paths in consideration for how to approach solving this problem, one being machine learning and the other being a more adaptive design. Machine learning would have involved labelling a lot of data with large potential for human error, especially since the beads share a similar appearance. The unique shape of the beads would have also meant that there would need to be numerous photos from various angles for every bead and bead size to label and train a machine learning based model. Even with all the labelled data, a machine learning model would require very consistent video inputs and conditions. After considering these factors, machine learning was not a good fit for this project and the timeframe we had. A adaptive approach was far more feasible and seemed to provide better results for the expected video inputs, which would have a degree of variance to them. The adaptive approach defines a distance through a reference, using landmark objects that can be visually identifiable. Landmarks include the diameter of the drum or the diameter of the largest visible ball, which are set by the user to define the pixel to millimetre ratio to calculate the detected circles sizes. This allows for videos to be different from each other with a good degree of variance, although there are conditions that will still produce a better output than others. The removal of the time that would have been spent on labelling data can now be directed towards other aspects of development, greatly reducing the expected project workload. The adaptive design should also be more open to future development and potential changes. 

 

Some major libraries used include OpenCV and PyAV. Research was done with these libraries focused on Python development.  

1.5.2 Summary of Relevant Tools 

Core 

Python 3.x 

High level coding language. 

OpenCV 

OpenCV is “an open source computer vision and machine learning library (OpenCV: About)”. OpenCV creates the infrastructure to detect objects from images and has many useful functions in its library. 

PyAV 

Pythonic binding for FFmpeg (PyAV Documentation). Controls access to media, particularly videos in this instance.  

NumPy 

Python package for scientific computing (NumPy).  

PyQt5 

GUI development option for interactive desktop applications (Geeks for Geeks, PyQt5). 

Tools 

Pytest 

Used to test certain cases more easily. 

Git 

Version control. 

YAML 

Human readable data serialization language. Meant for documents, they use Python style indentation. YAML is a superset of JSON. (RedHat) 

JSONL 

JSON Lines is a great format for log files. Every line is a valid JSON value. (JSON Lines) 

Powershell 

Used for scripting and automation of tasks. 

Algorithms 

Canny Edge Detection 

Hough Transform 

CLAHE 

Bilateral Filter 

NMS 

1.5.3 Challenges Addressed by our Project 

A major challenge in this project was separating the beads despite the very similar appearance they shared. To address this problem, we pre-processed the image through canny edge detection to find areas that had contrasted with their neighbouring areas. From there, it was possible to run another detection on it using Hough circles to find circles separated by the edges discovered using canny edge detection. 

 

1.6 Problem Statement 

Problem Description 

Professionals working with mini grinding mills require accurate, interpretable, and efficient tools to analyze and present bead behavior during mill operation. Current workflows rely heavily on manual inspection or generic video-review software, neither of which provides domain-specific capabilities such as bead-size classification or interactive visualization. As a result, engineers face challenges when attempting to communicate bead distribution, movement patterns, or size-dependent performance characteristics during technical presentations or client demonstrations. 

Furthermore, the dynamic nature of grinding environments—characterized by motion blur, varying lighting conditions, high-speed bead motion, and dense bead clustering—renders traditional video tools inadequate. There is a clear need for a specialized system capable of detecting beads of multiple sizes, classifying them accurately, and presenting the information in a visually coherent and computationally efficient manner. 

The MillPresenter project is designed to meet this need by developing a desktop application that: 

Automatically detects and classifies grinding beads in high-resolution (1080p, 59.94 fps) video footage. 

Displays bead classifications interactively, enabling users to toggle visibility of bead sizes in real time. 

Maintains smooth, uninterrupted video playback, essential for professional presentations. 

Operates reliably on standard Windows laptops, without requiring high-end hardware. 

Supports robust calibration workflows, allowing accurate pixel-to-millimeter conversion across diverse video sources. 

Together, these goals define the functional and operational scope of the system. 

 

Functional and Non-Functional Requirements 

1.6.1 Functional Requirements (FR) 

Video Ingestion & Handling 

FR-1.1: The system shall load video files in standard formats (MOV, MP4) using PyAV to ensure frame-accurate seeking. 

FR-1.2: The system shall automatically detect rotation metadata (e.g., from iPhones/Nikons) and rotate frames to the correct orientation upon loading. 

Calibration 

FR-2.1: The system shall provide a Drum Diameter Calibration mode, allowing the user to set the known physical diameter of the mill drum (e.g., 20 cm) to establish the px_per_mm ratio. 

FR-2.2: The system shall provide a Point-to-Point Calibration mode, allowing the user to click two edges of a reference object (e.g., a specific bead) and input its real-world size. 

FR-2.3: The system shall implement multi-frame averaging (sampling ~5 frames) during auto-calibration to reduce noise. 

 Region of Interest (ROI) & Masking 

FR-3.1: The system shall provide an interactive Circle Tool to define the ROI, matching the physical geometry of the mill drum. 

FR-3.2: The system shall utilize a Brightness Filter (threshold < 50) to ignore dark moving holes in the background of the drum. 

FR-3.3: The system shall auto-detect the drum rim using Hough Transforms to provide an initial ROI estimation. 

 Bead Detection Pipeline 

FR-4.1: The system shall employ a Dual-Path Detection strategy, running both Hough Circle Transform and Contour Analysis on every frame. 

FR-4.2: The system shall merge results from both paths using Non-Maximum Suppression (NMS) to remove duplicate detections. 

FR-4.3: The system shall apply Annulus Logic to identify and reject the inner holes of beads (concentric circles) to prevent double counting. 

FR-4.4: The system shall classify beads into four discrete bins: 4mm, 6mm, 8mm, and 10mm based on the calibrated pixel diameter. 

Visualization & Playback 

FR-5.1: The system shall allow users to toggle the visibility of specific bead size classes (e.g., "Hide 4mm") instantly without re-processing the video. 

FR-5.2: The system shall render colored circular overlays over the video at 60 FPS using cached detection data. 

FR-5.3: The overlays shall be drawn using a shared renderer (OverlayRenderer) to ensure visual consistency between the live UI and exported files. 

Export 

FR-6.1: The system shall export the processed video to an MP4 file with the currently active overlays "baked in". 

FR-6.2: The export process shall run on a background thread (ExportThread) and provide a progress dialog to the user. 

1.6.2 Non-Functional Requirements (NFR) 

Performance 

NFR-1: The detection phase acts as an offline process; speed is secondary to accuracy. However, the playback phase must not drop frames below 30 FPS, targeting 60 FPS for smoothness. 

NFR-2: Toggling size visibility must be near-instantaneous (< 50 ms). 

NFR-3: The application must be optimized for CPU-only execution environments, avoiding reliance on high-performance GPUs. 

Reliability 

NFR-4: The system shall use JSONL (append-only) for caching to prevent data corruption in the event of a crash during long processing runs. 

 

Usability 

NFR-4: Calibration steps shall be guided via the status bar or on-screen instructions to minimize user error 

NFR-5: The interface must be intuitive and accessible to non-technical users, requiring minimal training. 

Portability  

NFR-6: The application should function as a standalone desktop tool for Windows or macOS (platform finalized per client requirements). 

Constraints, and Assumptions 

Constraints 

Performance Constraint: The system must maintain smooth playback, with class-toggle operations completing in under 50 ms. 

Hardware Constraint: Must operate effectively on standard laptops with optional GPU acceleration. 

Environmental Constraints: The computer vision pipeline must handle image noise, motion blur, specular reflections, and occlusions. 

Calibration Constraint: Accurate calibration must be achievable across various video sources and camera setups. 

Detection Accuracy Constraint: The system is expected to achieve 80–90% detection accuracy under typical conditions. 

Assumptions 

Calibration targets or reference objects are visible or obtainable. 

Beads remain sufficiently visible despite motion and lighting variations. 

Videos are recorded under conditions representative of standard mill operation. 

Users have access to stable camera mounts and non-corrupted video files. 

Design Challenges 

The development of a robust detection and presentation system for grinding bead analysis introduces several technical challenges: 

Annular Geometry: Grinding beads possess hollow centers, generating two concentric edges that may result in false detections. 

Motion Blur: High-speed bead motion at elevated RPM diminishes contour clarity and complicates circle fitting. 

Specular Reflections: Metallic beads often produce glare that interferes with edge detection. 

Bead Overlap: Dense clustering and partial occlusion reduce detection recall and require sophisticated filtering. 

Background Interference: Mill components and environmental elements produce circular shapes or textures similar to beads. 

Real-Time Constraints: The need for smooth playback prohibits performing detection during live viewing, requiring an alternative architecture. 

Proposed Solution 

To address these challenges and satisfy both functional and non-functional requirements, MillPresenter implements the following solution strategy: 

A dual-path detection pipeline, combining Hough Circle Transform and contour-based methods to improve robustness across varied environments. 

Non-Maximum Suppression (NMS) techniques to refine overlapping detections and reduce redundancy. 

Annulus-filtering logic to eliminate false detections originating from bead interior holes. 

Advanced preprocessing (e.g., bilateral filtering, CLAHE) to improve contrast and reduce glare. 

Region-of-interest (ROI) masking tools to isolate valid detection regions and minimize background interference. 

An offline computation model, in which all detections are performed prior to playback and results are cached, enabling seamless real-time toggling without performance degradation. 

This integrated solution ensures that MillPresenter delivers the necessary precision, usability, and responsiveness required for professional industrial presentations. 

1.7 Methodology 

System Architecture Overview 

The system follows a modular architecture that isolates video decoding, computer vision processing, result caching, and GUI rendering into discrete components. This separation ensures maintainability, promotes independent development and testing, and allows future extensions without destabilizing the entire system. 

Key modules include: 

FrameLoader for video decoding and frame extraction. 

VisionProcessor for preprocessing, detection, and classification. 

ResultsCache for efficient disk and memory-based storage. 

OverlayRenderer for drawing overlays consistently across playback and exports. 

ProcessorOrchestrator for managing offline detection execution. 

MainWindow and associated UI controllers for user interaction and visualization. 

Detection Pipeline 

The detection pipeline consists of four major stages: 

Preprocessing: 

Grayscale conversion 

Bilateral filtering to suppress noise and glare 

CLAHE to improve local contrast 

Dual-Path Detection: 

Hough Circle Transform for robust detection in dense or occluded areas. 

Contour detection and circularity analysis for precise detection in isolated contexts. 

Filtering and Deduplication: 

ROI validation 

Brightness thresholding to remove hole artifacts 

Annulus detection to reject internal circles 

Non-maximum suppression for candidate merging 

Classification: 

Conversion from pixel radius to millimeters 

Assignment to size bins according to calibrated ranges 

Confidence scoring based on contour quality and edge strength 

 

 

 

 

 

 

Caching Strategy 

The system employs a two-tiered caching strategy: 

Disk-based JSONL Cache: 

Stores frame-level detections in an append-only, fault-resistant format. 

In-Memory Ring Buffer: 

Retains recent detections for rapid retrieval during playback and scrubbing. 

Calibration Methods 

Supported calibration techniques include: 

Ring-based calibration, the primary method, leveraging known circular reference dimensions. 

Two-point calibration, using user-defined reference points. 

Known-bead calibration, based on beads with known real-world diameters. 

ROI Masking 

ROI masking is achieved through: 

Automated estimation of the mill's circular region. 

A user-adjustable interactive circle tool. 

Margin-based mask generation to ensure consistent exclusion of irrelevant areas.  

Text Box 2, Caixa de textoA red and blue container with many small round objects

AI-generated content may be incorrect. 

 

Development Methodology 

A test-driven development (TDD) approach guided implementation, supplemented by continuous integration, modular code design, and comprehensive unit and integration testing. 

1.8 Implementation 

Technology Stack 

The application is developed primarily using Python, integrating: 

PyQt6 for interface design 

OpenCV for image processing 

PyAV for video decoding 

NumPy, PyYAML, and other standard scientific libraries 

Core Components 

Each module is implemented with attention to performance, modularity, and clarity: 

FrameLoader provides accurate seeking, frame iteration, and hardware-accelerated decoding. 

VisionProcessor executes preprocessing, dual detection paths, filtering logic, and classification. 

ResultsCache ensures efficient read/write access to large detection datasets. 

OverlayRenderer draws diameter-scaled overlays with consistent color coding. 

ProcessorOrchestrator executes batch detection with progress tracking and fault tolerance. 

User Interface Design 

The interface supports: 

Smooth playback with overlay rendering 

Class toggling 

Calibration and ROI tools 

Progress reporting for detection and export workflows 

The design emphasizes clarity, responsiveness, and usability for non-technical users. 

Export Functionality 

The system supports MP4 export with pre-rendered overlays, ensuring consistency between live presentation and exported materials. 

Testing Framework 

Testing includes: 

Unit tests for all major modules 

Integration tests for end-to-end workflows 

Synthetic and real-world video testing 

UI interaction tests for calibration and ROI tools 

1.9 Results and Analysis 

Key Results 

 

Tables, Graphs, Visual Aids 

 

Functionality 

 

Performance Metrics 

The main output of the program, the detected beads, are difficult to confidently say they are accurately detected as it is hard to differentiate them visibly. The best method to confirm accuracy is to check if the circles visibly match the shape of the bead it is detecting. This can be done by viewing a paused frame and checking if the detected circled matches the expected area. The detection parameters can be tweaked if the circles are not as accurate as desired. 

 

Results Analyzed 

 

 

1.10 Discussion 

Significance of Results 

The results demonstrate the feasibility of achieving near-real-time responsiveness with high-quality overlays by decoupling detection from playback. The system provides a practical and accessible solution for industrial presentations, balancing performance with accuracy. 

Comparison to Existing Tools 

MillPresenter outperforms generic video tools by offering domain-specific features and reliable high-frame-rate playback with customizable overlays. Although deep learning approaches may offer improved accuracy, they require more development effort and hardware resources. 

Limitations and Constraints 

Current limitations largely arise from: 

Single-camera reliance 

Classical CV sensitivity to extreme blur and reflection 

Restricted ROI geometry 

Future Work 

Potential extensions include: 

Integration of lightweight deep learning models 

Multi-video batch processing 

Bead tracking across frames 

Statistical reporting tools 

Multi-camera synchronization 

Cloud-based processing pipelines 

1.11 Conclusion 
"create table of content" 
This project successfully delivers a robust, presentation-oriented video analysis system for grinding mill bead classification. Through a combination of classical computer vision techniques, efficient caching strategies, and a user-centered interface design, MillPresenter achieves high performance, interpretability, and usability. The separation of detection from playback enables smooth real-time interaction during presentations, while the modular architecture supports ongoing refinement and future enhancements. 

The work contributes to industrial computer vision applications by demonstrating how domain-specific constraints can be addressed effectively through tailored algorithmic design and thoughtful system architecture. Future expansions may incorporate machine learning, advanced analytics, or multi-camera perspectives to further enhance the system’s capabilities. 

1.12 References 

Geeks for Geeks, PyQt5, “Python | Introduction to PyQt5”, https://www.geeksforgeeks.org/python/python-introduction-to-pyqt5/  

Hux, “Open CV: How does the BGR2GRAY function work?,” Stack Overflow, Apr. 06, 2020. https://stackoverflow.com/questions/61058335/open-cv-how-does-the-bgr2gray-function-work 

JSON Lines, “JSON Lines: Documentation for the JSON Lines text file format”, https://jsonlines.org/  

NumPy, “What is NumPy?”, https://numpy.org/doc/stable/user/whatisnumpy.html  

“OpenCV: Canny Edge Detection.” https://docs.opencv.org/4.x/da/d22/tutorial_py_canny.html 

“OpenCV: About” https://opencv.org/about/  

“OpenCV: Histograms - 2: Histogram Equalization.” https://docs.opencv.org/4.x/d5/daf/tutorial_py_histogram_equalization.html 

“PyQt6 Tutorial 2025, Create Python GUIs with Qt,” Python GUIs, May 19, 2025. https://www.pythonguis.com/pyqt6-tutorial/ 

PyAV, “PyAV Documentation” , https://pyav.org/docs/stable/  

PyAV, “Installation — PyAV 9.0.3.dev0 documentation.” https://pyav.org/docs/develop/overview/installation.html 

RedHat, “What is YAML?”, https://www.redhat.com/en/topics/automation/what-is-yaml  

1.13 Appendices 

 

A black text with black letters

AI-generated content may be incorrect. 

2 Individual Contributions 

 

 

 

 

 

Class Toggle Interaction  

 

 

 

 

 

 

 

A red and blue container with many small round objects

AI-generated content may be incorrect. 

 

 

Pre Processing (Grey, CLAHE, Blur) 

 

 

 

Golden Frames + Mask (OpenCV alternative) 

 

 

 

 

 

 

 

 

Hough Circle Detection first phase,  just a broad net. The filtration is done later on the pipeline. 

 

 

 

 

 

 

CLHE  

CLHE (Contrast Limited Adaptive Histogram Equalization (CLAHE))  

Orange circles (0.2~0.3) -->  low confidence,   Green Circles (0.7+) --->  high confidence  

Score = (Brightness * 0.7) + (Texture * 0.3) 

 

 

 

 

Distribution 

 

 

Filter & Count  

 

 

 

 

 

 

 

 

 

 

 