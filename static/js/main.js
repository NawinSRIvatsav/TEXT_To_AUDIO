// VoxFlow.ai - Main Frontend Logic

document.addEventListener('DOMContentLoaded', () => {
    initToasts();
    initWordCounters();
    initFileDropzone();
    initAudioPlayers();
});

// 1. Toast Notification Auto-Dismiss
function initToasts() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.style.transition = 'all 0.5s ease';
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(50px)';
            setTimeout(() => toast.remove(), 500);
        }, 5000);
    });
}

// 2. Tab switching logic for uploads
let currentUploadMode = 'text'; // 'text' or 'file'

function setUploadMode(mode) {
    currentUploadMode = mode;
    const tabText = document.getElementById('tabDirectText');
    const tabFile = document.getElementById('tabFileUpload');
    const textContainer = document.getElementById('textModeContainer');
    const fileContainer = document.getElementById('fileModeContainer');
    
    const textarea = document.getElementById('id_text');
    const fileInput = document.getElementById('id_file');

    if (mode === 'text') {
        tabText.classList.add('active');
        tabFile.classList.remove('active');
        textContainer.classList.add('active-mode');
        fileContainer.classList.remove('active-mode');
        // Make text required if no file is chosen
        if (textarea) textarea.required = true;
        if (fileInput) fileInput.required = false;
    } else {
        tabFile.classList.add('active');
        tabText.classList.remove('active');
        fileContainer.classList.add('active-mode');
        textContainer.classList.remove('active-mode');
        // Make file required if text is empty
        if (textarea) textarea.required = false;
        // Don't enforce file input required directly, let clean() handle it, or keep it optional
    }
}

// 3. Word and Character Counters
function initWordCounters() {
    const textarea = document.getElementById('id_text');
    if (!textarea) return;

    // Initially make text field required
    textarea.required = true;

    const charCountEl = document.getElementById('charCount');
    const wordCountDisplayEl = document.getElementById('wordCountDisplay');
    
    textarea.addEventListener('input', () => {
        const text = textarea.value;
        const charCount = text.length;
        
        // Count words, filter out empty elements from splitting spaces
        const words = text.trim().split(/\s+/).filter(word => word.length > 0);
        const wordCount = words.length;

        charCountEl.innerText = `${charCount} characters`;
        wordCountDisplayEl.innerText = `${wordCount} words`;
    });
}

// 4. Drag & Drop File Zone
function initFileDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('id_file');
    if (!dropzone || !fileInput) return;

    // Click handler is inline in HTML: onclick="document.getElementById('id_file').click()"

    fileInput.addEventListener('change', (e) => {
        handleFileSelection(fileInput.files[0]);
    });

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
        }, false);
    });

    dropzone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileSelection(files[0]);
        }
    });
}

function handleFileSelection(file) {
    const fileInfo = document.getElementById('selectedFileInfo');
    const fileNameText = document.getElementById('fileName');
    const dropzoneIcon = document.querySelector('.dropzone-icon');
    const dropzoneMainText = document.querySelector('.dropzone-text');
    const dropzoneSubtext = document.querySelector('.dropzone-subtext');

    if (file) {
        fileNameText.innerText = `${file.name} (${formatBytes(file.size)})`;
        fileInfo.classList.add('active');
        
        // Hide standard dropzone labels to keep it clean
        if (dropzoneIcon) dropzoneIcon.style.opacity = '0.3';
        if (dropzoneMainText) dropzoneMainText.style.display = 'none';
        if (dropzoneSubtext) dropzoneSubtext.style.display = 'none';
    } else {
        clearSelectedFile();
    }
}

function clearSelectedFile(event) {
    if (event) event.stopPropagation(); // Stop trigger file selection dialog again
    
    const fileInput = document.getElementById('id_file');
    const fileInfo = document.getElementById('selectedFileInfo');
    const fileNameText = document.getElementById('fileName');
    const dropzoneIcon = document.querySelector('.dropzone-icon');
    const dropzoneMainText = document.querySelector('.dropzone-text');
    const dropzoneSubtext = document.querySelector('.dropzone-subtext');

    if (fileInput) fileInput.value = '';
    if (fileNameText) fileNameText.innerText = 'No file chosen';
    if (fileInfo) fileInfo.classList.remove('active');

    if (dropzoneIcon) dropzoneIcon.style.opacity = '1';
    if (dropzoneMainText) dropzoneMainText.style.display = 'block';
    if (dropzoneSubtext) dropzoneSubtext.style.display = 'block';
}

function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// 5. Form Submission & Synthesizer Loading Overlay
function showProcessingSpinner(event) {
    const textarea = document.getElementById('id_text');
    const fileInput = document.getElementById('id_file');
    const loader = document.getElementById('processingLoader');
    const loaderSubtitle = document.getElementById('loaderSubtitle');

    let textHasContent = textarea && textarea.value.trim().length > 0;
    let fileHasContent = fileInput && fileInput.files.length > 0;

    // Verify inputs before activating loading panel
    if (currentUploadMode === 'text' && !textHasContent) {
        return; // standard HTML validation handles it
    }
    if (currentUploadMode === 'file' && !fileHasContent) {
        alert("Please upload a .txt or .pdf file first.");
        event.preventDefault();
        return;
    }

    if (fileHasContent && currentUploadMode === 'file') {
        loaderSubtitle.innerText = "Extracting text structure from your uploaded document...";
    } else {
        loaderSubtitle.innerText = "Parsing speech waves and synthesizing audio signals...";
    }

    if (loader) {
        loader.classList.add('active');
    }
}

// 6. Custom Audio Player Logic (Works for both guest player and dashboard list players)
let activeAudio = null;
let activePlayButton = null;

function initAudioPlayers() {
    // This connects default media events to progress updates
    const audios = document.querySelectorAll('audio');
    audios.forEach(audio => {
        audio.addEventListener('timeupdate', () => {
            updateProgressBar(audio);
        });
        audio.addEventListener('ended', () => {
            const btn = document.querySelector(`button[onclick*="${audio.id}"]`);
            if (btn) {
                btn.innerHTML = '<i class="fa-solid fa-play"></i>';
            }
            const progress = document.getElementById(`${audio.id}_progress`) || document.getElementById('guestPlayerProgress');
            if (progress) progress.style.width = '0%';
            const timeEl = document.getElementById(`${audio.id}_time`) || document.getElementById('guestPlayerTime');
            if (timeEl) timeEl.innerText = formatTime(0);
            
            if (activeAudio === audio) {
                activeAudio = null;
                activePlayButton = null;
            }
        });
    });
}

function togglePlayer(audioId, btnElement) {
    const audio = document.getElementById(audioId);
    if (!audio) return;

    if (activeAudio && activeAudio !== audio) {
        // Pause previously playing audio
        activeAudio.pause();
        if (activePlayButton) {
            activePlayButton.innerHTML = '<i class="fa-solid fa-play"></i>';
        }
    }

    if (audio.paused) {
        audio.play();
        btnElement.innerHTML = '<i class="fa-solid fa-pause"></i>';
        activeAudio = audio;
        activePlayButton = btnElement;
    } else {
        audio.pause();
        btnElement.innerHTML = '<i class="fa-solid fa-play"></i>';
        activeAudio = null;
        activePlayButton = null;
    }
}

function updateProgressBar(audio) {
    const duration = audio.duration || 0;
    const currentTime = audio.currentTime || 0;
    
    // Find target progress fill bar and time indicators
    const isGuest = audio.id === 'guestAudioSource';
    const progressFill = isGuest 
        ? document.getElementById('guestPlayerProgress') 
        : document.getElementById(`${audio.id}_progress`);
        
    const timeDisplay = isGuest 
        ? document.getElementById('guestPlayerTime') 
        : document.getElementById(`${audio.id}_time`);

    if (duration > 0 && progressFill) {
        const percentage = (currentTime / duration) * 100;
        progressFill.style.width = `${percentage}%`;
    }

    if (timeDisplay) {
        timeDisplay.innerText = formatTime(currentTime);
    }
}

function seekAudio(audioId, event) {
    const audio = document.getElementById(audioId);
    if (!audio) return;

    const container = event.currentTarget;
    const rect = container.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const percentage = clickX / rect.width;
    
    if (audio.duration) {
        audio.currentTime = percentage * audio.duration;
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// 7. AJAX Deletion on Dashboard
function ajaxDelete(event, conversionId) {
    event.preventDefault();
    
    if (!confirm("Are you sure you want to delete this audio asset? This cannot be undone.")) {
        return;
    }

    const form = event.currentTarget;
    const url = form.action;
    const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;
    const row = document.getElementById(`conversion_row_${conversionId}`);

    fetch(url, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // Success animation
            if (row) {
                row.style.transition = 'all 0.5s ease';
                row.style.opacity = '0';
                row.style.transform = 'translateY(15px)';
                setTimeout(() => {
                    row.remove();
                    
                    // Check if dashboard list is empty now
                    const list = document.getElementById('conversionsList');
                    if (list && list.children.length === 0) {
                        location.reload(); // reload to show empty state card
                    }
                }, 500);
            }
            
            // Add a floating success notification
            showTemporaryToast('success', data.message);
        } else {
            showTemporaryToast('error', 'Failed to delete audio file.');
        }
    })
    .catch(error => {
        console.error('Error deleting conversion:', error);
        showTemporaryToast('error', 'Network error. Please try again.');
    });
}

function showTemporaryToast(type, text) {
    // Create new toast container if missing
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const iconClass = type === 'success' ? 'fa-circle-check' : 'fa-circle-xmark';
    toast.innerHTML = `
        <i class="fa-solid ${iconClass}"></i>
        <span class="toast-message">${text}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);
    
    // Trigger auto-dismiss
    setTimeout(() => {
        toast.style.transition = 'all 0.5s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}
