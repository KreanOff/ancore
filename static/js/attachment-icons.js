(function (global) {
    const BI_BY_TYPE = {
        image: 'bi-file-earmark-image',
        pdf: 'bi-file-earmark-pdf',
        document: 'bi-file-earmark-text',
        archive: 'bi-file-earmark-zip',
        default: 'bi-file-earmark',
    };

    const TYPE_COLORS = {
        image: { color: '#1976d2', bg: '#e3f2fd' },
        pdf: { color: '#c2185b', bg: '#fce4ec' },
        document: { color: '#388e3c', bg: '#e8f5e8' },
        archive: { color: '#f57c00', bg: '#fff3e0' },
        default: { color: '#616161', bg: '#f5f5f5' },
    };

    function normalizeExt(ext) {
        if (!ext) return '';
        return String(ext).replace(/^\./, '').toLowerCase();
    }

    function extensionToTypeClass(ext) {
        const e = normalizeExt(ext);
        if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(e)) return 'image';
        if (e === 'pdf') return 'pdf';
        if (['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf'].includes(e)) return 'document';
        if (['zip', 'rar', '7z', 'tar', 'gz'].includes(e)) return 'archive';
        return 'default';
    }

    function getBiClass(typeClass) {
        return BI_BY_TYPE[typeClass] || BI_BY_TYPE.default;
    }

    function getTypeStyle(typeClass) {
        return TYPE_COLORS[typeClass] || TYPE_COLORS.default;
    }

    function iconHtml(typeClass, size) {
        size = size || 'md';
        const bi = getBiClass(typeClass);
        return `<div class="attachment-icon attachment-icon--${size} ${typeClass}"><i class="bi ${bi}" aria-hidden="true"></i></div>`;
    }

    function iconHtmlByExtension(ext, size) {
        return iconHtml(extensionToTypeClass(ext), size);
    }

    function createIconElement(typeClass, size) {
        const wrap = document.createElement('div');
        wrap.className = `attachment-icon attachment-icon--${size || 'md'} ${typeClass}`;
        const icon = document.createElement('i');
        icon.className = `bi ${getBiClass(typeClass)}`;
        icon.setAttribute('aria-hidden', 'true');
        wrap.appendChild(icon);
        return wrap;
    }

    global.AttachmentIcons = {
        BI_BY_TYPE,
        extensionToTypeClass,
        getBiClass,
        getTypeStyle,
        iconHtml,
        iconHtmlByExtension,
        createIconElement,
        PAPERCLIP: 'bi-paperclip',
        UPLOAD: 'bi-cloud-arrow-up',
        TRASH: 'bi-trash',
    };
})(typeof window !== 'undefined' ? window : globalThis);
