// Options page JavaScript functionality
// COMP 4910 Final Project

document.addEventListener('DOMContentLoaded', function() {
    const selectedFilesList = document.getElementById('selectedFilesList');
    const detectionRadios = document.querySelectorAll('input[name="detectionMode"]');
    const highQualityCheckbox = document.getElementById('highQuality');
    const emailNotificationCheckbox = document.getElementById('emailNotification');
    const startProcessingBtn = document.getElementById('startProcessingBtn');
    const fileCount = document.getElementById('fileCount');
    const selectedMode = document.getElementById('selectedMode');
    const estimatedTime = document.getElementById('estimatedTime');

    let selectedFiles = [];
    let processingOptions = {
        detectionMode: '6mm',
        highQuality: true,
        emailNotification: false
    };

    // Initialize page
    initializePage();

    function initializePage() {
        // Load selected files from storage
        selectedFiles = VideoProcessingApp.storage.loadFiles();
        processingOptions = VideoProcessingApp.storage.loadOptions();

        // Display selected files
        displaySelectedFiles();
        
        // Update processing summary
        updateProcessingSummary();
        
        // Set up event listeners
        setupEventListeners();
        
        // Update UI based on saved options
        updateUIFromOptions();
    }

    function displaySelectedFiles() {
        if (selectedFiles.length === 0) {
            selectedFilesList.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-exclamation-triangle fa-2x mb-2"></i>
                    <p>No files selected. Please go back to upload files.</p>
                    <button class="btn btn-primary" onclick="goBack()">
                        <i class="fas fa-arrow-left me-2"></i>
                        Back to Upload
                    </button>
                </div>
            `;
            return;
        }

        selectedFilesList.innerHTML = '';
        selectedFiles.forEach((file, index) => {
            const fileItem = createFileItem(file, index);
            selectedFilesList.appendChild(fileItem);
        });
    }

    function createFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        fileItem.innerHTML = `
            <div class="d-flex align-items-center">
                <div class="file-icon me-3">
                    <i class="fas fa-video text-primary"></i>
                </div>
                <div>
                    <h6 class="mb-1">${file.name}</h6>
                    <small class="text-muted">${VideoProcessingApp.utils.formatFileSize(file.size)}</small>
                </div>
            </div>
            <div class="file-actions">
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        return fileItem;
    }

    function setupEventListeners() {
        // Detection mode selection
        detectionRadios.forEach(radio => {
            radio.addEventListener('change', handleDetectionModeChange);
        });

        // High quality checkbox
        highQualityCheckbox.addEventListener('change', handleHighQualityChange);

        // Email notification checkbox
        emailNotificationCheckbox.addEventListener('change', handleEmailNotificationChange);

        // Start processing button
        startProcessingBtn.addEventListener('click', startProcessing);

        // Detection option cards click handlers
        document.querySelectorAll('.detection-option').forEach(option => {
            option.addEventListener('click', handleDetectionOptionClick);
        });
    }

    function handleDetectionModeChange(event) {
        processingOptions.detectionMode = event.target.value;
        updateProcessingSummary();
        updateDetectionCards();
        saveOptions();
    }

    function handleHighQualityChange(event) {
        processingOptions.highQuality = event.target.checked;
        updateProcessingSummary();
        saveOptions();
    }

    function handleEmailNotificationChange(event) {
        processingOptions.emailNotification = event.target.checked;
        saveOptions();
    }

    function handleDetectionOptionClick(event) {
        const mode = event.currentTarget.dataset.mode;
        const radio = document.getElementById(`detection${mode}`);
        radio.checked = true;
        processingOptions.detectionMode = mode;
        updateProcessingSummary();
        updateDetectionCards();
        saveOptions();
    }

    function updateDetectionCards() {
        document.querySelectorAll('.detection-option').forEach(option => {
            option.classList.remove('selected');
            const mode = option.dataset.mode;
            if (mode === processingOptions.detectionMode) {
                option.classList.add('selected');
            }
        });
    }

    function updateProcessingSummary() {
        fileCount.textContent = selectedFiles.length;
        selectedMode.textContent = processingOptions.detectionMode;
        
        // Calculate estimated time based on file count and detection mode
        const baseTime = selectedFiles.length * 2; // 2 minutes per file
        const modeMultiplier = {
            '4mm': 1.5,  // More precise = longer processing
            '6mm': 1.0,  // Standard
            '8mm': 0.8,  // Less precise = faster processing
            '10mm': 0.6  // Least precise = fastest processing
        };
        
        const estimatedMinutes = Math.ceil(baseTime * modeMultiplier[processingOptions.detectionMode]);
        estimatedTime.textContent = `${estimatedMinutes}-${estimatedMinutes + 2} minutes`;
    }

    function updateUIFromOptions() {
        // Set detection mode
        const detectionRadio = document.getElementById(`detection${processingOptions.detectionMode}`);
        if (detectionRadio) {
            detectionRadio.checked = true;
        }

        // Set checkboxes
        highQualityCheckbox.checked = processingOptions.highQuality;
        emailNotificationCheckbox.checked = processingOptions.emailNotification;

        // Update detection cards
        updateDetectionCards();
    }

    function saveOptions() {
        VideoProcessingApp.storage.saveOptions(processingOptions);
        VideoProcessingApp.processingOptions = processingOptions;
    }

    async function startProcessing() {
        if (selectedFiles.length === 0) {
            VideoProcessingApp.utils.showNotification('No files selected for processing.', 'warning');
            return;
        }

        // Disable button and show loading state
        startProcessingBtn.disabled = true;
        startProcessingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting Processing...';

        try {
            // Simulate API call to start processing
            const jobId = await simulateStartProcessing();
            
            // Save job ID and navigate to render page
            localStorage.setItem('currentJobId', jobId);
            VideoProcessingApp.navigation.goToRender(jobId);
            
        } catch (error) {
            console.error('Processing start error:', error);
            VideoProcessingApp.utils.showNotification('Failed to start processing. Please try again.', 'error');
            
            // Reset button state
            startProcessingBtn.disabled = false;
            startProcessingBtn.innerHTML = '<i class="fas fa-play me-2"></i>Start Processing';
        }
    }

    async function simulateStartProcessing() {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Generate mock job ID
        const jobId = 'job_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        
        // Save processing job data
        const jobData = {
            id: jobId,
            files: selectedFiles,
            options: processingOptions,
            status: 'processing',
            startTime: new Date().toISOString(),
            estimatedDuration: calculateEstimatedDuration()
        };
        
        localStorage.setItem('jobData_' + jobId, JSON.stringify(jobData));
        
        return jobId;
    }

    function calculateEstimatedDuration() {
        const baseTime = selectedFiles.length * 2; // 2 minutes per file
        const modeMultiplier = {
            '4mm': 1.5,
            '6mm': 1.0,
            '8mm': 0.8,
            '10mm': 0.6
        };
        
        return Math.ceil(baseTime * modeMultiplier[processingOptions.detectionMode]);
    }

    function removeFile(index) {
        selectedFiles.splice(index, 1);
        VideoProcessingApp.storage.saveFiles(selectedFiles);
        displaySelectedFiles();
        updateProcessingSummary();
    }

    // Make functions globally available
    window.removeFile = removeFile;
    window.goBack = () => VideoProcessingApp.navigation.goToUpload();
});

// Additional options functionality
function toggleDetectionMode(mode) {
    const radio = document.getElementById(`detection${mode}`);
    if (radio) {
        radio.checked = true;
        document.dispatchEvent(new Event('change'));
    }
}

function resetOptions() {
    processingOptions = {
        detectionMode: '6mm',
        highQuality: true,
        emailNotification: false
    };
    
    // Update UI
    document.getElementById('detection6mm').checked = true;
    document.getElementById('highQuality').checked = true;
    document.getElementById('emailNotification').checked = false;
    
    updateDetectionCards();
    updateProcessingSummary();
    saveOptions();
}


