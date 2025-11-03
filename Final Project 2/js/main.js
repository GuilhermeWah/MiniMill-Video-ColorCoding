// Main JavaScript file for Molycop MiniMill Ball Detection
// COMP 4910 Final Project

// Global variables
let selectedFiles = [];
let processingOptions = {
    detectionMode: '6mm',
    highQuality: true,
    emailNotification: false
};

// API Configuration
const API_BASE_URL = 'http://localhost:3000/api'; // Update with your backend URL

// Utility Functions
const utils = {
    // Format file size
    formatFileSize: (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Format time duration
    formatTime: (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    },

    // Show notification
    showNotification: (message, type = 'info') => {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';

        const notification = document.createElement('div');
        notification.className = `alert ${alertClass} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    },

    // Validate file type
    validateFileType: (file) => {
        const allowedTypes = [
            'video/mp4',
            'video/avi',
            'video/mov',
            'video/wmv',
            'video/mkv',
            'video/webm'
        ];
        return allowedTypes.includes(file.type);
    },

    // Validate file size (500MB limit)
    validateFileSize: (file) => {
        const maxSize = 500 * 1024 * 1024; // 500MB in bytes
        return file.size <= maxSize;
    }
};

// API Functions
const api = {
    // Upload files
    uploadFiles: async (files, options) => {
        const formData = new FormData();
        
        // Add files to form data
        files.forEach((file, index) => {
            formData.append(`file_${index}`, file);
        });
        
        // Add processing options
        formData.append('detectionMode', options.detectionMode);
        formData.append('highQuality', options.highQuality);
        formData.append('emailNotification', options.emailNotification);

        try {
            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Upload error:', error);
            throw error;
        }
    },

    // Check processing status
    checkStatus: async (jobId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/status/${jobId}`);
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Status check error:', error);
            throw error;
        }
    },

    // Get processing results
    getResults: async (jobId) => {
        try {
            const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
            
            if (!response.ok) {
                throw new Error(`Results fetch failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Results fetch error:', error);
            throw error;
        }
    },

    // Download processed video
    downloadVideo: async (jobId, quality = 'high') => {
        try {
            const response = await fetch(`${API_BASE_URL}/download/${jobId}?quality=${quality}`);
            
            if (!response.ok) {
                throw new Error(`Download failed: ${response.statusText}`);
            }

            // Create download link
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `processed_video_${jobId}.mp4`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (error) {
            console.error('Download error:', error);
            throw error;
        }
    }
};

// Local Storage Functions
const storage = {
    // Save selected files
    saveFiles: (files) => {
        const fileData = files.map(file => ({
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified
        }));
        localStorage.setItem('selectedFiles', JSON.stringify(fileData));
    },

    // Load selected files
    loadFiles: () => {
        const data = localStorage.getItem('selectedFiles');
        return data ? JSON.parse(data) : [];
    },

    // Save processing options
    saveOptions: (options) => {
        localStorage.setItem('processingOptions', JSON.stringify(options));
    },

    // Load processing options
    loadOptions: () => {
        const data = localStorage.getItem('processingOptions');
        return data ? JSON.parse(data) : processingOptions;
    },

    // Clear all data
    clear: () => {
        localStorage.removeItem('selectedFiles');
        localStorage.removeItem('processingOptions');
        localStorage.removeItem('currentJobId');
    }
};

// Navigation Functions
const navigation = {
    // Navigate to upload page
    goToUpload: () => {
        window.location.href = 'upload.html';
    },

    // Navigate to options page
    goToOptions: () => {
        window.location.href = 'options.html';
    },

    // Navigate to render page
    goToRender: (jobId) => {
        localStorage.setItem('currentJobId', jobId);
        window.location.href = 'render.html';
    },

    // Navigate to results page
    goToResults: (jobId) => {
        localStorage.setItem('currentJobId', jobId);
        window.location.href = 'results.html';
    },

    // Go back to previous page
    goBack: () => {
        window.history.back();
    }
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Load saved data
    selectedFiles = storage.loadFiles();
    processingOptions = storage.loadOptions();

    // Initialize page-specific functionality
    const currentPage = window.location.pathname.split('/').pop();
    
    switch (currentPage) {
        case 'index.html':
        case '':
            initializeHomePage();
            break;
        case 'upload.html':
            initializeUploadPage();
            break;
        case 'options.html':
            initializeOptionsPage();
            break;
        case 'render.html':
            initializeRenderPage();
            break;
        case 'results.html':
            initializeResultsPage();
            break;
    }
});

// Page-specific initialization functions
function initializeHomePage() {
    // Add any home page specific initialization here
    console.log('Home page initialized');
}

function initializeUploadPage() {
    // This will be implemented in upload.js
    console.log('Upload page initialized');
}

function initializeOptionsPage() {
    // This will be implemented in options.js
    console.log('Options page initialized');
}

function initializeRenderPage() {
    // This will be implemented in render.js
    console.log('Render page initialized');
}

function initializeResultsPage() {
    // This will be implemented in results.js
    console.log('Results page initialized');
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    utils.showNotification('An unexpected error occurred. Please try again.', 'error');
});

// Export for use in other files
window.VideoProcessingApp = {
    utils,
    api,
    storage,
    navigation,
    selectedFiles,
    processingOptions
};


