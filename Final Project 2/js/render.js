// Render page JavaScript functionality
// COMP 4910 Final Project

document.addEventListener('DOMContentLoaded', function() {
    const currentFileName = document.getElementById('currentFileName');
    const detectionMode = document.getElementById('detectionMode');
    const progressBar = document.getElementById('progressBar');
    const progressPercentage = document.getElementById('progressPercentage');
    const elapsedTime = document.getElementById('elapsedTime');
    const estimatedTime = document.getElementById('estimatedTime');
    const processingSpeed = document.getElementById('processingSpeed');
    const cancelProcessingBtn = document.getElementById('cancelProcessingBtn');

    let jobId = null;
    let jobData = null;
    let startTime = null;
    let statusInterval = null;
    let timeInterval = null;

    // Initialize page
    initializePage();

    function initializePage() {
        // Get job ID from storage
        jobId = localStorage.getItem('currentJobId');
        
        if (!jobId) {
            VideoProcessingApp.utils.showNotification('No processing job found. Please start a new processing job.', 'error');
            setTimeout(() => {
                VideoProcessingApp.navigation.goToUpload();
            }, 2000);
            return;
        }

        // Load job data
        loadJobData();
        
        // Start processing simulation
        startProcessingSimulation();
        
        // Set up event listeners
        setupEventListeners();
    }

    function loadJobData() {
        const savedJobData = localStorage.getItem('jobData_' + jobId);
        if (savedJobData) {
            jobData = JSON.parse(savedJobData);
            startTime = new Date(jobData.startTime);
            
            // Update UI with job data
            updateJobInfo();
        } else {
            // Fallback to default values
            jobData = {
                files: [{ name: 'sample_video.mp4' }],
                options: { detectionMode: '6mm' }
            };
            startTime = new Date();
        }
    }

    function updateJobInfo() {
        if (jobData && jobData.files && jobData.files.length > 0) {
            currentFileName.textContent = jobData.files[0].name;
        }
        
        if (jobData && jobData.options) {
            detectionMode.textContent = jobData.options.detectionMode;
        }
    }

    function setupEventListeners() {
        cancelProcessingBtn.addEventListener('click', cancelProcessing);
    }

    function startProcessingSimulation() {
        // Start time tracking
        startTimeTracking();
        
        // Start progress simulation
        simulateProgress();
        
        // Start status polling (simulated)
        startStatusPolling();
    }

    function startTimeTracking() {
        timeInterval = setInterval(updateTimeDisplay, 1000);
    }

    function updateTimeDisplay() {
        const now = new Date();
        const elapsed = Math.floor((now - startTime) / 1000);
        const elapsedMinutes = Math.floor(elapsed / 60);
        const elapsedSeconds = elapsed % 60;
        
        elapsedTime.textContent = `${elapsedMinutes}:${elapsedSeconds.toString().padStart(2, '0')}`;
        
        // Update processing speed (simulated)
        const speed = (0.8 + Math.random() * 0.4).toFixed(1);
        processingSpeed.textContent = speed + 'x';
    }

    function simulateProgress() {
        let progress = 0;
        const targetProgress = 100;
        const duration = 30000; // 30 seconds for demo
        const increment = targetProgress / (duration / 100);
        
        const progressInterval = setInterval(() => {
            progress += increment + (Math.random() - 0.5) * 2;
            
            if (progress > targetProgress) {
                progress = targetProgress;
                clearInterval(progressInterval);
                completeProcessing();
            }
            
            updateProgressBar(progress);
            updateProcessingSteps(progress);
        }, 100);
    }

    function updateProgressBar(progress) {
        const roundedProgress = Math.round(progress);
        progressBar.style.width = roundedProgress + '%';
        progressPercentage.textContent = roundedProgress + '%';
    }

    function updateProcessingSteps(progress) {
        const steps = [
            { id: 'step-upload', threshold: 0 },
            { id: 'step-analysis', threshold: 25 },
            { id: 'step-processing', threshold: 60 },
            { id: 'step-finalizing', threshold: 90 }
        ];

        steps.forEach(step => {
            const stepElement = document.getElementById(step.id);
            if (stepElement) {
                if (progress >= step.threshold) {
                    stepElement.classList.add('active');
                    
                    if (progress > step.threshold + 20) {
                        stepElement.classList.add('completed');
                        stepElement.classList.remove('active');
                    }
                }
            }
        });
    }

    function startStatusPolling() {
        // Simulate status checking every 2 seconds
        statusInterval = setInterval(checkProcessingStatus, 2000);
    }

    async function checkProcessingStatus() {
        try {
            // In a real application, this would call the API
            // const status = await VideoProcessingApp.api.checkStatus(jobId);
            
            // Simulate status check
            const status = await simulateStatusCheck();
            
            if (status.status === 'completed') {
                clearInterval(statusInterval);
                clearInterval(timeInterval);
                completeProcessing();
            } else if (status.status === 'failed') {
                clearInterval(statusInterval);
                clearInterval(timeInterval);
                handleProcessingError(status.error);
            }
        } catch (error) {
            console.error('Status check error:', error);
        }
    }

    async function simulateStatusCheck() {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 500));
        
        // Simulate completion after 30 seconds
        const elapsed = (new Date() - startTime) / 1000;
        if (elapsed > 30) {
            return { status: 'completed' };
        }
        
        return { status: 'processing', progress: Math.min(elapsed / 30 * 100, 95) };
    }

    function completeProcessing() {
        // Update final progress
        updateProgressBar(100);
        updateProcessingSteps(100);
        
        // Show completion message
        VideoProcessingApp.utils.showNotification('Processing completed successfully!', 'success');
        
        // Navigate to results page after a short delay
        setTimeout(() => {
            VideoProcessingApp.navigation.goToResults(jobId);
        }, 2000);
    }

    function handleProcessingError(error) {
        VideoProcessingApp.utils.showNotification(`Processing failed: ${error}`, 'error');
        
        // Reset UI
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        
        // Show retry option
        setTimeout(() => {
            if (confirm('Processing failed. Would you like to try again?')) {
                VideoProcessingApp.navigation.goToOptions();
            } else {
                VideoProcessingApp.navigation.goToUpload();
            }
        }, 2000);
    }

    function cancelProcessing() {
        if (confirm('Are you sure you want to cancel processing? This action cannot be undone.')) {
            // Clear intervals
            if (statusInterval) clearInterval(statusInterval);
            if (timeInterval) clearInterval(timeInterval);
            
            // Show cancellation message
            VideoProcessingApp.utils.showNotification('Processing cancelled.', 'warning');
            
            // Navigate back to upload page
            setTimeout(() => {
                VideoProcessingApp.navigation.goToUpload();
            }, 1500);
        }
    }

    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (statusInterval) clearInterval(statusInterval);
        if (timeInterval) clearInterval(timeInterval);
    });
});

// Additional render functionality
function pauseProcessing() {
    // In a real application, this would pause the processing job
    VideoProcessingApp.utils.showNotification('Processing paused.', 'info');
}

function resumeProcessing() {
    // In a real application, this would resume the processing job
    VideoProcessingApp.utils.showNotification('Processing resumed.', 'success');
}

function getProcessingLogs() {
    // In a real application, this would fetch processing logs
    return [
        'Starting video analysis...',
        'Detecting objects with 6mm precision...',
        'Processing frame 1 of 150...',
        'Applying detection algorithms...',
        'Finalizing output...'
    ];
}


