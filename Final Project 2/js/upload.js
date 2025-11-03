// Upload page JavaScript functionality
// COMP 4910 Final Project

document.addEventListener('DOMContentLoaded', function() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('videoFile');
    const filePreview = document.getElementById('filePreview');
    const fileList = document.getElementById('fileList');
    const validationMessages = document.getElementById('validationMessages');
    const uploadProgress = document.getElementById('uploadProgress');
    const nextStepBtn = document.getElementById('nextStepBtn');

    let selectedFiles = [];

    // Initialize upload area
    initializeUploadArea();

    // File input change handler
    fileInput.addEventListener('change', handleFileSelect);

    // Drag and drop handlers
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('click', () => fileInput.click());

    // Next step button handler
    nextStepBtn.addEventListener('click', proceedToOptions);

    function initializeUploadArea() {
        // Set up initial state
        updateUploadArea();
    }

    function handleFileSelect(event) {
        const files = Array.from(event.target.files);
        processFiles(files);
    }

    function handleDragOver(event) {
        event.preventDefault();
        uploadArea.classList.add('dragover');
    }

    function handleDragLeave(event) {
        event.preventDefault();
        uploadArea.classList.remove('dragover');
    }

    function handleDrop(event) {
        event.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = Array.from(event.dataTransfer.files);
        processFiles(files);
    }

    function processFiles(files) {
        // Clear previous validation messages
        clearValidationMessages();

        // Validate files
        const validFiles = [];
        const errors = [];

        files.forEach((file, index) => {
            // Check file type
            if (!VideoProcessingApp.utils.validateFileType(file)) {
                errors.push(`${file.name}: Unsupported file type. Please use MP4, AVI, MOV, WMV, MKV, or WebM.`);
                return;
            }

            // Check file size
            if (!VideoProcessingApp.utils.validateFileSize(file)) {
                errors.push(`${file.name}: File too large. Maximum size is 500MB.`);
                return;
            }

            validFiles.push(file);
        });

        // Show validation errors
        if (errors.length > 0) {
            showValidationErrors(errors);
        }

        // Update selected files
        selectedFiles = validFiles;
        VideoProcessingApp.selectedFiles = selectedFiles;

        // Save to storage
        VideoProcessingApp.storage.saveFiles(selectedFiles);

        // Update UI
        updateFilePreview();
        updateUploadArea();
        updateNextStepButton();
    }

    function updateFilePreview() {
        if (selectedFiles.length === 0) {
            filePreview.style.display = 'none';
            return;
        }

        filePreview.style.display = 'block';
        fileList.innerHTML = '';

        selectedFiles.forEach((file, index) => {
            const fileItem = createFileItem(file, index);
            fileList.appendChild(fileItem);
        });
    }

    function createFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-icon">
                <i class="fas fa-video"></i>
            </div>
            <div class="file-info">
                <h6>${file.name}</h6>
                <small>${VideoProcessingApp.utils.formatFileSize(file.size)}</small>
            </div>
            <div class="file-actions">
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        return fileItem;
    }

    function removeFile(index) {
        selectedFiles.splice(index, 1);
        VideoProcessingApp.selectedFiles = selectedFiles;
        VideoProcessingApp.storage.saveFiles(selectedFiles);
        
        updateFilePreview();
        updateUploadArea();
        updateNextStepButton();
    }

    function updateUploadArea() {
        if (selectedFiles.length > 0) {
            uploadArea.innerHTML = `
                <div class="upload-content text-center">
                    <i class="fas fa-check-circle fa-4x text-success mb-3"></i>
                    <h4>Files Selected Successfully</h4>
                    <p class="text-muted">${selectedFiles.length} file(s) ready for processing</p>
                    <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('videoFile').click()">
                        <i class="fas fa-plus me-2"></i>
                        Add More Files
                    </button>
                </div>
            `;
        } else {
            uploadArea.innerHTML = `
                <div class="upload-content text-center">
                    <i class="fas fa-cloud-upload-alt fa-4x text-muted mb-3"></i>
                    <h4>Drag & Drop Your Video Here</h4>
                    <p class="text-muted">or click to browse files</p>
                    <button type="button" class="btn btn-outline-primary" onclick="document.getElementById('videoFile').click()">
                        <i class="fas fa-folder-open me-2"></i>
                        Choose Files
                    </button>
                </div>
            `;
        }
    }

    function updateNextStepButton() {
        nextStepBtn.disabled = selectedFiles.length === 0;
    }

    function showValidationErrors(errors) {
        const errorHtml = errors.map(error => 
            `<div class="alert alert-danger alert-dismissible fade show">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${error}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>`
        ).join('');

        validationMessages.innerHTML = errorHtml;
    }

    function clearValidationMessages() {
        validationMessages.innerHTML = '';
    }

    function proceedToOptions() {
        if (selectedFiles.length === 0) {
            VideoProcessingApp.utils.showNotification('Please select at least one video file.', 'warning');
            return;
        }

        // Save current state
        VideoProcessingApp.storage.saveFiles(selectedFiles);
        
        // Navigate to options page
        VideoProcessingApp.navigation.goToOptions();
    }

    // Make functions globally available
    window.removeFile = removeFile;
});

// Additional upload functionality
function simulateUpload() {
    const progressBar = document.querySelector('#uploadProgress .progress-bar');
    const progressText = document.querySelector('#uploadProgress small');
    
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 100) progress = 100;
        
        progressBar.style.width = progress + '%';
        progressText.textContent = `Uploading files... ${Math.round(progress)}%`;
        
        if (progress >= 100) {
            clearInterval(interval);
            progressText.textContent = 'Upload complete!';
            setTimeout(() => {
                document.getElementById('uploadProgress').style.display = 'none';
                VideoProcessingApp.navigation.goToOptions();
            }, 1000);
        }
    }, 200);
}

// File validation helper
function validateFiles(files) {
    const errors = [];
    const validFiles = [];

    files.forEach(file => {
        // Check file type
        const allowedTypes = [
            'video/mp4',
            'video/avi', 
            'video/mov',
            'video/wmv',
            'video/mkv',
            'video/webm'
        ];

        if (!allowedTypes.includes(file.type)) {
            errors.push(`${file.name}: Unsupported file type`);
            return;
        }

        // Check file size (500MB limit)
        const maxSize = 500 * 1024 * 1024;
        if (file.size > maxSize) {
            errors.push(`${file.name}: File too large (max 500MB)`);
            return;
        }

        validFiles.push(file);
    });

    return { validFiles, errors };
}



