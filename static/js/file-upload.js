class FileUploadManager {
    constructor() {
        this.dropZone = document.getElementById('drop-zone');
        this.fileInput = document.getElementById('file-input');
        this.browseBtn = document.getElementById('browse-btn');
        this.fileList = document.getElementById('file-list');
        this.files = [];
        this.isTaskIssueUpload = Boolean(
            this.fileList &&
            this.fileList.classList.contains('tasks-file-list') &&
            this.fileList.closest('.tasks-issue-page')
        );

        this.init();
    }

    init() {
        if (!this.fileInput) return;

        if (this.browseBtn) {
            this.browseBtn.addEventListener('click', () => this.triggerFileInputClick());
        }

        if (this.dropZone) {
            this.dropZone.addEventListener('click', () => this.triggerFileInputClick());
        }

        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        if (!this.dropZone) return;

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

        this.fileList.style.display = this.isTaskIssueUpload ? 'grid' : 'block';

        this.files.forEach((file, index) => {
            const fileItem = this.createFileItem(file, index);
            this.fileList.appendChild(fileItem);
        });
        AttachmentIcons.render(this.fileList);
    }

    createFileItem(file, index) {
        if (this.isTaskIssueUpload) {
            return this.createTaskIssueFileItem(file, index);
        }

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
        removeBtn.innerHTML = AttachmentIcons.TRASH_SVG;
        removeBtn.addEventListener('click', () => this.removeFile(index));
        fileItem.appendChild(removeBtn);

        return fileItem;
    }

    createTaskIssueFileItem(file, index) {
        const fileItem = document.createElement('div');
        fileItem.className = 'tasks-attachment-card tasks-attachment-card--pending';

        const fileInfo = document.createElement('div');
        fileInfo.className = 'tasks-attachment-info';

        const fileIcon = this.createFileIcon(file);
        fileInfo.appendChild(fileIcon);

        const fileDetails = document.createElement('span');
        fileDetails.className = 'tasks-attachment-details';

        const fileName = document.createElement('span');
        fileName.className = 'tasks-attachment-name';
        fileName.textContent = file.name;
        fileDetails.appendChild(fileName);

        const fileSize = document.createElement('span');
        fileSize.className = 'tasks-attachment-size';
        fileSize.textContent = this.formatFileSize(file.size);
        fileDetails.appendChild(fileSize);

        fileInfo.appendChild(fileDetails);
        fileItem.appendChild(fileInfo);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'tasks-delete-attach-btn';
        removeBtn.title = 'Usuń załącznik';
        removeBtn.setAttribute('aria-label', `Usuń ${file.name}`);
        removeBtn.innerHTML = AttachmentIcons.TRASH_SVG;
        removeBtn.addEventListener('click', () => this.removeFile(index));
        fileItem.appendChild(removeBtn);

        return fileItem;
    }

    createFileIcon(file) {
        const extension = this.getFileExtension(file.name);
        const typeClass = AttachmentIcons.extensionToTypeClass(extension);
        return AttachmentIcons.createIconElement(typeClass, 'md');
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
        this.dispatchUploadUpdated();
    }

    dispatchUploadUpdated() {
        document.dispatchEvent(new CustomEvent('ancore:file-upload-updated', {
            detail: {
                form: this.fileInput.form,
                input: this.fileInput,
                fileCount: this.files.length,
            },
        }));
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

function initFileUploadManager() {
    const fileInput = document.getElementById('file-input');
    if (!fileInput || fileInput.dataset.fileUploadInitialized === 'true') return;

    fileInput.dataset.fileUploadInitialized = 'true';
    new FileUploadManager();
}

// Initialize the file upload manager when the DOM is ready
document.addEventListener('DOMContentLoaded', initFileUploadManager);
document.addEventListener('ancore:content-loaded', initFileUploadManager);
