(function (global) {
    const BI_BY_TYPE = {
        image: 'bi-file-earmark-image',
        pdf: 'bi-file-earmark-pdf',
        document: 'bi-file-earmark-text',
        archive: 'bi-file-earmark-zip',
        default: 'bi-file-earmark',
    };

    const TYPE_COLORS = {
        image: { color: '#1f2328', bg: '#ADD8E6' },
        pdf: { color: '#c2185b', bg: '#fce4ec' },
        document: { color: '#388e3c', bg: '#e8f5e8' },
        archive: { color: '#f57c00', bg: '#fff3e0' },
        default: { color: '#616161', bg: '#f5f5f5' },
    };

    const PAPERCLIP_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M15 7l-6.5 6.5a1.5 1.5 0 0 0 3 3l6.5 -6.5a3 3 0 0 0 -6 -6l-6.5 6.5a4.5 4.5 0 0 0 9 9l6.5 -6.5"/></svg>';
    const TRASH_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path stroke="none" d="M0 0h24v24H0z" fill="none"/><path d="M4 7l16 0"/><path d="M10 11l0 6"/><path d="M14 11l0 6"/><path d="M5 7l1 12a2 2 0 0 0 2 2h8a2 2 0 0 0 2 -2l1 -12"/><path d="M9 7v-3a1 1 0 0 1 1 -1h4a1 1 0 0 1 1 1v3"/></svg>';

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
        PAPERCLIP_SVG,
        UPLOAD: 'bi-cloud-arrow-up',
        TRASH_SVG,
    };
})(typeof window !== 'undefined' ? window : globalThis);
