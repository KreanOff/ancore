(function (global) {
    const LUCIDE_BY_TYPE = {
        image: 'file-image',
        pdf: 'file-text',
        document: 'file-text',
        archive: 'file-archive',
        default: 'file',
    };

    const TYPE_COLORS = {
        image: { color: '#1f2328', bg: '#ADD8E6' },
        pdf: { color: '#c2185b', bg: '#fce4ec' },
        document: { color: '#388e3c', bg: '#e8f5e8' },
        archive: { color: '#f57c00', bg: '#fff3e0' },
        default: { color: '#616161', bg: '#f5f5f5' },
    };

    const PAPERCLIP_SVG = '<i data-lucide="paperclip" aria-hidden="true"></i>';
    const TRASH_SVG = '<i data-lucide="trash-2" aria-hidden="true"></i>';

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

    function getLucideName(typeClass) {
        return LUCIDE_BY_TYPE[typeClass] || LUCIDE_BY_TYPE.default;
    }

    function getTypeStyle(typeClass) {
        return TYPE_COLORS[typeClass] || TYPE_COLORS.default;
    }

    function iconHtml(typeClass, size) {
        size = size || 'md';
        const icon = getLucideName(typeClass);
        return `<div class="attachment-icon attachment-icon--${size} ${typeClass}"><i data-lucide="${icon}" aria-hidden="true"></i></div>`;
    }

    function iconHtmlByExtension(ext, size) {
        return iconHtml(extensionToTypeClass(ext), size);
    }

    function createIconElement(typeClass, size) {
        const wrap = document.createElement('div');
        wrap.className = `attachment-icon attachment-icon--${size || 'md'} ${typeClass}`;
        const icon = global.AncoreIcons
            ? global.AncoreIcons.create(getLucideName(typeClass))
            : document.createElement('i');
        if (!global.AncoreIcons) {
            icon.setAttribute('data-lucide', getLucideName(typeClass));
            icon.setAttribute('aria-hidden', 'true');
        }
        wrap.appendChild(icon);
        renderIcons(wrap);
        return wrap;
    }

    function renderIcons(root) {
        if (global.AncoreIcons) {
            requestAnimationFrame(() => global.AncoreIcons.render(root || document));
        }
    }

    global.AttachmentIcons = {
        LUCIDE_BY_TYPE,
        extensionToTypeClass,
        getLucideName,
        getTypeStyle,
        iconHtml,
        iconHtmlByExtension,
        createIconElement,
        PAPERCLIP: 'paperclip',
        PAPERCLIP_SVG,
        UPLOAD: 'cloud-upload',
        TRASH_SVG,
        render: renderIcons,
    };
})(typeof window !== 'undefined' ? window : globalThis);
