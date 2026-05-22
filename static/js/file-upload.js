class FileUploadManager {
    constructor() {
        this.dropZone = document.getElementById('drop-zone');
        this.fileInput = document.getElementById('file-input');
        this.browseBtn = document.getElementById('browse-btn');
        this.fileList = document.getElementById('file-list');
        this.files = [];

        this.init();
    }

    init() {
        if (!this.dropZone || !this.fileInput || !this.browseBtn) return;

        // Click events
        this.browseBtn.addEventListener('click', () => this.triggerFileInputClick());
        this.dropZone.addEventListener('click', () => this.triggerFileInputClick());

        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        // Drag and drop events
        this.dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropZone.classList.add('dragover');
        });

        this.dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
        });

        this.dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropZone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });

        // Prevent default drag events on the whole document
        document.addEventListener('dragover', (e) => e.preventDefault());
        document.addEventListener('drop', (e) => e.preventDefault());
    }

    triggerFileInputClick() {
        // Temporarily re-enable input if disabled, then click, then disable again
        const wasDisabled = this.fileInput.disabled;
        if (wasDisabled) {
            this.fileInput.disabled = false;
        }
        // Clear the input so the same file can be selected again if needed
        this.fileInput.value = '';
        this.fileInput.click();
        // Re-disable if it was disabled before (after click is triggered)
        if (wasDisabled) {
            // Use setTimeout to ensure the click event is processed first
            setTimeout(() => {
                this.fileInput.disabled = true;
            }, 0);
        }
    }

    handleFiles(files) {
        const newFiles = Array.from(files);
        console.log('[FileUpload] Processing files:', newFiles.map(f => f.name));

        // Filter out duplicate files
        newFiles.forEach(file => {
            const isDuplicate = this.files.some(existingFile =>
                existingFile.name === file.name &&
                existingFile.size === file.size
            );

            if (!isDuplicate) {
                this.files.push(file);
            }
        });

        console.log('[FileUpload] Total files after update:', this.files.length);
        this.updateFileList();
        this.updateFileInput();
    }

    updateFileList() {
        if (!this.fileList) return;

        this.fileList.innerHTML = '';

        if (this.files.length === 0) {
            this.fileList.style.display = 'none';
            return;
        }

        this.fileList.style.display = 'block';

        this.files.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            this.fileList.appendChild(fileItem);
        });
    }

    createFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';

        const fileInfo = document.createElement('div');
        fileInfo.className = 'file-info';

        const fileIcon = this.createFileIcon(file);
        fileInfo.appendChild(fileIcon);

        const fileDetails = document.createElement('div');
        fileDetails.className = 'file-details';

        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name;
        fileDetails.appendChild(fileName);

        const fileSize = document.createElement('div');
        fileSize.className = 'file-size';
        fileSize.textContent = this.formatFileSize(file.size);
        fileDetails.appendChild(fileSize);

        fileInfo.appendChild(fileDetails);
        fileItem.appendChild(fileInfo);

        const removeBtn = document.createElement('button');
        removeBtn.className = 'file-remove';
        removeBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
        `;
        removeBtn.addEventListener('click', () => this.removeFile(index));
        fileItem.appendChild(removeBtn);

        return fileItem;
    }

    createFileIcon(file) {
        const icon = document.createElement('div');
        icon.className = 'file-icon';

        const extension = this.getFileExtension(file.name);

        if (this.isImageFile(extension)) {
            icon.classList.add('image');
            icon.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                </svg>
            `;
        } else if (extension === '.pdf') {
            icon.classList.add('pdf');
            icon.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                    <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
            `;
        } else if (this.isDocumentFile(extension)) {
            icon.classList.add('document');
            icon.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                    <line x1="16" y1="13" x2="8" y2="13"></line>
                    <line x1="16" y1="17" x2="8" y2="17"></line>
                </svg>
            `;
        } else if (this.isArchiveFile(extension)) {
            icon.classList.add('archive');
            icon.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 8V21a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8"></path>
                    <rect x="1" y="3" width="22" height="5" rx="1"></rect>
                    <line x1="10" y1="12" x2="14" y2="12"></line>
                </svg>
            `;
        } else {
            icon.classList.add('default');
            icon.innerHTML = `
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                    <polyline points="13 2 13 9 20 9"></polyline>
                </svg>
            `;
        }

        return icon;
    }

    getFileExtension(filename) {
        const lastDot = filename.lastIndexOf('.');
        return lastDot === -1 ? '' : filename.toLowerCase().slice(lastDot);
    }

    isImageFile(extension) {
        const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
        return imageExtensions.includes(extension);
    }

    isDocumentFile(extension) {
        const docExtensions = ['.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf'];
        return docExtensions.includes(extension);
    }

    isArchiveFile(extension) {
        const archiveExtensions = ['.zip', '.rar', '.7z', '.tar', '.gz'];
        return archiveExtensions.includes(extension);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    removeFile(index) {
        this.files.splice(index, 1);
        this.updateFileList();
        this.updateFileInput();
    }

    updateFileInput() {
        // Always use fallback approach for better cross-browser compatibility
        // and to avoid issues with read-only input.files in some browsers
        this.createFallbackFileInputs();
    }

    createFallbackFileInputs() {
        // Remove any existing fallback inputs
        const existingContainer = document.getElementById('fallback-file-inputs');
        if (existingContainer) {
            existingContainer.remove();
        }

        // If no files, re-enable the original input and clear it
        if (this.files.length === 0) {
            this.fileInput.disabled = false;
            this.fileInput.value = '';
            return;
        }

        // Create container for fallback inputs
        const container = document.createElement('div');
        container.id = 'fallback-file-inputs';
        container.style.display = 'none';

        // Create a file input for each file
        this.files.forEach((file, index) => {
            const input = document.createElement('input');
            input.type = 'file';
            input.name = 'attachments';
            input.className = 'fallback-attachment-input';

            // Create a FileList with this single file
            const dt = new DataTransfer();
            dt.items.add(file);
            input.files = dt.files;

            container.appendChild(input);
        });

        // Insert after the original file input
        this.fileInput.parentNode.insertBefore(container, this.fileInput.nextSibling);

        // Disable the original input so it doesn't send empty files
        this.fileInput.disabled = true;
    }

    getFiles() {
        return this.files;
    }
}

// Initialize the file upload manager when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new FileUploadManager();
});
