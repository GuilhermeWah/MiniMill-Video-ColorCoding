// Results page JavaScript functionality
// COMP 4910 Final Project

document.addEventListener('DOMContentLoaded', function() {
    const video = document.getElementById('processedVideo');
    const videoSource = document.getElementById('videoSource');
    const playPauseBtn = document.getElementById('playPauseBtn');
    const muteBtn = document.getElementById('muteBtn');
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const currentTime = document.getElementById('currentTime');
    const totalTime = document.getElementById('totalTime');
    const downloadHighQuality = document.getElementById('downloadHighQuality');
    const downloadStandard = document.getElementById('downloadStandard');
    const shareBtn = document.getElementById('shareBtn');
    const processAnotherBtn = document.getElementById('processAnotherBtn');
    const viewDetailsBtn = document.getElementById('viewDetailsBtn');

    let jobId = null;
    let jobData = null;

    // Initialize page
    initializePage();

    function initializePage() {
        jobId = localStorage.getItem('currentJobId');
        
        if (!jobId) {
            VideoProcessingApp.utils.showNotification('No results found. Please process a video first.', 'error');
            setTimeout(() => VideoProcessingApp.navigation.goToUpload(), 2000);
            return;
        }

        loadJobData();
        setupEventListeners();
        loadResults();
    }

    function loadJobData() {
        const savedJobData = localStorage.getItem('jobData_' + jobId);
        if (savedJobData) {
            jobData = JSON.parse(savedJobData);
            updateJobInfo();
        }
    }

    function updateJobInfo() {
        if (jobData && jobData.files && jobData.files.length > 0) {
            document.getElementById('originalFileName').textContent = jobData.files[0].name;
            document.getElementById('originalFileSize').textContent = VideoProcessingApp.utils.formatFileSize(jobData.files[0].size);
        }
        
        if (jobData && jobData.options) {
            document.getElementById('processingMode').textContent = jobData.options.detectionMode;
        }
    }

    function setupEventListeners() {
        // Video controls
        playPauseBtn.addEventListener('click', togglePlayPause);
        muteBtn.addEventListener('click', toggleMute);
        fullscreenBtn.addEventListener('click', toggleFullscreen);
        
        // Download buttons
        downloadHighQuality.addEventListener('click', () => downloadVideo('high'));
        downloadStandard.addEventListener('click', () => downloadVideo('standard'));
        
        // Action buttons
        shareBtn.addEventListener('click', shareResults);
        processAnotherBtn.addEventListener('click', processAnother);
        viewDetailsBtn.addEventListener('click', viewDetails);
        
        // Video events
        video.addEventListener('timeupdate', updateTimeDisplay);
        video.addEventListener('loadedmetadata', updateTotalTime);
        video.addEventListener('play', () => updatePlayPauseButton(true));
        video.addEventListener('pause', () => updatePlayPauseButton(false));
    }

    async function loadResults() {
        try {
            // Simulate loading results
            const results = await simulateLoadResults();
            
            // Set video source
            videoSource.src = results.videoUrl;
            video.load();
            
            // Update statistics
            updateStatistics(results.statistics);
            
        } catch (error) {
            console.error('Error loading results:', error);
            VideoProcessingApp.utils.showNotification('Failed to load results.', 'error');
        }
    }

    async function simulateLoadResults() {
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        return {
            videoUrl: 'data:video/mp4;base64,', // Placeholder - would be actual video URL
            statistics: {
                objectsDetected: 127,
                accuracyScore: 94.2,
                processingFrames: 3240,
                processingSpeed: 1.8
            }
        };
    }

    function updateStatistics(stats) {
        document.getElementById('objectsDetected').textContent = stats.objectsDetected;
        document.getElementById('accuracyScore').textContent = stats.accuracyScore + '%';
        document.getElementById('processingFrames').textContent = stats.processingFrames;
        document.getElementById('processingSpeed').textContent = stats.processingSpeed + 'x';
    }

    function togglePlayPause() {
        if (video.paused) {
            video.play();
        } else {
            video.pause();
        }
    }

    function toggleMute() {
        video.muted = !video.muted;
        const icon = muteBtn.querySelector('i');
        icon.className = video.muted ? 'fas fa-volume-mute' : 'fas fa-volume-up';
    }

    function toggleFullscreen() {
        if (video.requestFullscreen) {
            video.requestFullscreen();
        }
    }

    function updatePlayPauseButton(isPlaying) {
        const icon = playPauseBtn.querySelector('i');
        icon.className = isPlaying ? 'fas fa-pause' : 'fas fa-play';
    }

    function updateTimeDisplay() {
        currentTime.textContent = VideoProcessingApp.utils.formatTime(video.currentTime);
    }

    function updateTotalTime() {
        totalTime.textContent = VideoProcessingApp.utils.formatTime(video.duration);
    }

    async function downloadVideo(quality) {
        try {
            VideoProcessingApp.utils.showNotification(`Starting download (${quality} quality)...`, 'info');
            
            // Simulate download
            await VideoProcessingApp.api.downloadVideo(jobId, quality);
            
            VideoProcessingApp.utils.showNotification('Download completed!', 'success');
        } catch (error) {
            console.error('Download error:', error);
            VideoProcessingApp.utils.showNotification('Download failed. Please try again.', 'error');
        }
    }

    function shareResults() {
        const shareUrl = window.location.origin + '/results/' + jobId;
        
        if (navigator.share) {
            navigator.share({
                title: 'Processed Video Results',
                text: 'Check out my processed video results!',
                url: shareUrl
            });
        } else {
            // Fallback to clipboard
            navigator.clipboard.writeText(shareUrl).then(() => {
                VideoProcessingApp.utils.showNotification('Share link copied to clipboard!', 'success');
            });
        }
    }

    function processAnother() {
        VideoProcessingApp.storage.clear();
        VideoProcessingApp.navigation.goToUpload();
    }

    function viewDetails() {
        // Show detailed processing information
        const details = {
            'Job ID': jobId,
            'Processing Time': '1:23',
            'Detection Mode': jobData?.options?.detectionMode || '6mm',
            'Quality': jobData?.options?.highQuality ? 'High' : 'Standard',
            'Objects Detected': '127',
            'Accuracy': '94.2%'
        };
        
        let detailsHtml = '<div class="table-responsive"><table class="table table-sm">';
        for (const [key, value] of Object.entries(details)) {
            detailsHtml += `<tr><td><strong>${key}:</strong></td><td>${value}</td></tr>`;
        }
        detailsHtml += '</table></div>';
        
        // Show in modal or alert
        alert('Processing Details:\n\n' + Object.entries(details).map(([k, v]) => `${k}: ${v}`).join('\n'));
    }
});


