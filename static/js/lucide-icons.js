(function (global) {
    const LEGACY_ICON_MAP = {
        '': 'circle',
        '☆': 'star',
        'check': 'circle-check',
        '✅': 'circle-check',
        '☑️': 'square-check',
        '✔️': 'check',
        '✖️': 'x',
        '❌': 'circle-x',
        '➕': 'plus',
        '➖': 'minus',
        '📁': 'folder',
        '📂': 'folder-open',
        '📑': 'files',
        '📄': 'file-text',
        '📃': 'file',
        '📜': 'scroll-text',
        '📔': 'book',
        '📕': 'book-open',
        '📗': 'book-open',
        '📘': 'book-open',
        '📙': 'book-open',
        '📓': 'notebook',
        '📒': 'notebook-tabs',
        '🗒️': 'notepad-text',
        '🧷': 'paperclip',
        '🖇️': 'paperclip',
        '📎': 'paperclip',
        '🔖': 'bookmark',
        '🔗': 'link',
        '🗝️': 'key-round',
        '🔒': 'lock',
        '🔓': 'lock-open',
        '🏛️': 'landmark',
        '🏫': 'school',
        '🏟️': 'ticket',
        '🏪': 'store',
        '🏬': 'building',
        '🏢': 'building-2',
        '🏭': 'factory',
        '🏗️': 'construction',
        '🚛': 'truck',
        '🚚': 'truck',
        '🚢': 'ship',
        '✈️': 'plane',
        '🚀': 'rocket',
        '📦': 'package',
        '🛒': 'shopping-cart',
        '🧺': 'shopping-basket',
        '💡': 'lightbulb',
        '⚙️': 'settings',
        '🛠️': 'wrench',
        '🧰': 'briefcase-business',
        '💼': 'briefcase-business',
        '💻': 'laptop',
        '🎨': 'palette',
        '🙂': 'smile',
        '💰': 'wallet',
        '🌍': 'globe',
        '🌎': 'globe',
        '🌏': 'globe',
        '🌿': 'leaf',
        '🍕': 'pizza',
        '🎓': 'graduation-cap',
        '💚': 'heart-pulse',
        '🔣': 'shapes',
        '📡': 'satellite-dish',
        '📶': 'wifi',
        '🛜': 'wifi',
        '🎖️': 'medal',
        '🏅': 'award',
        '🥇': 'trophy',
        '🔍': 'search',
        '🔎': 'search',
        '🔔': 'bell',
        '📣': 'megaphone',
        '📢': 'megaphone',
        '🚨': 'siren',
        '⛔': 'ban',
        '⭕': 'circle',
        '⚠️': 'triangle-alert',
        '❤️': 'heart',
        '⭐': 'star',
        '🌟': 'sparkles',
        '✨': 'sparkles',
        '💫': 'sparkles',
        '🔥': 'flame',
        '⚡': 'zap',
        '🗓️': 'calendar-days',
        '📅': 'calendar',
        '⏱️': 'timer',
        '⏲️': 'timer',
        '⌛': 'hourglass',
        '⏳': 'hourglass',
        '📊': 'chart-column',
        '📈': 'chart-no-axes-combined',
        '🎯': 'target',
        '🧩': 'puzzle',
        '🌐': 'globe',
        '☁️': 'cloud',
        '📍': 'map-pin',
        '📌': 'pin',
        '🧭': 'compass',
        '🏷️': 'tag',
        '🧾': 'receipt',
        '📰': 'newspaper',
        '🗞️': 'newspaper',
        '🗄️': 'archive',
        '🗃️': 'archive',
        '📇': 'contact',
        '🧮': 'calculator',
        '🧪': 'flask-conical',
        '🖥️': 'monitor',
    };

    const LUCIDE_ALIASES = {
        alert: 'triangle-alert',
        archivebox: 'archive',
        bin: 'trash-2',
        calendar: 'calendar-days',
        dashboard: 'layout-dashboard',
        delete: 'trash-2',
        edit: 'pencil',
        filearchive: 'file-archive',
        fileimage: 'file-image',
        filepdf: 'file-text',
        filetext: 'file-text',
        folderopen: 'folder-open',
        home: 'house',
        kanbanboard: 'kanban',
        logout: 'log-out',
        paperclip: 'paperclip',
        settings: 'settings',
        trash: 'trash-2',
        upload: 'cloud-upload',
        userprofile: 'user-round',
    };

    function kebabToPascal(name) {
        return String(name || '')
            .split('-')
            .filter(Boolean)
            .map(part => part.charAt(0).toUpperCase() + part.slice(1))
            .join('');
    }

    function normalizeIconName(name, fallback) {
        const defaultName = fallback || 'circle';
        const raw = String(name || '').trim();
        if (!raw) return defaultName;
        if (LEGACY_ICON_MAP[raw]) return LEGACY_ICON_MAP[raw];

        const kebab = raw
            .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
            .replace(/_/g, '-')
            .replace(/\s+/g, '-')
            .replace(/[^a-zA-Z0-9-]/g, '')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '')
            .toLowerCase();

        const aliased = LUCIDE_ALIASES[kebab.replace(/-/g, '')] || LUCIDE_ALIASES[kebab] || kebab;
        return aliased || defaultName;
    }

    function hasLucideIcon(name) {
        if (!global.lucide || !global.lucide.icons) return true;
        return Boolean(global.lucide.icons[kebabToPascal(name)]);
    }

    function safeIconName(name, fallback) {
        const normalized = normalizeIconName(name, fallback);
        if (hasLucideIcon(normalized)) return normalized;
        const normalizedFallback = normalizeIconName(fallback || 'circle', 'circle');
        return hasLucideIcon(normalizedFallback) ? normalizedFallback : 'circle';
    }

    function iconHtml(name, options) {
        const opts = options || {};
        const iconName = safeIconName(name, opts.fallback);
        const className = opts.className ? ` class="${opts.className}"` : '';
        const label = opts.label ? ` aria-label="${opts.label}"` : ' aria-hidden="true"';
        const title = opts.title ? ` title="${opts.title}"` : '';
        const strokeWidth = opts.strokeWidth ? ` stroke-width="${opts.strokeWidth}"` : '';
        return `<i data-lucide="${iconName}"${className}${label}${title}${strokeWidth}></i>`;
    }

    function createIcon(name, options) {
        const opts = options || {};
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', safeIconName(name, opts.fallback));
        if (opts.className) icon.className = opts.className;
        if (opts.label) {
            icon.setAttribute('aria-label', opts.label);
        } else {
            icon.setAttribute('aria-hidden', 'true');
        }
        if (opts.title) icon.setAttribute('title', opts.title);
        if (opts.strokeWidth) icon.setAttribute('stroke-width', opts.strokeWidth);
        return icon;
    }

    function normalizeDataLucide(root) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('[data-lucide]').forEach(icon => {
            const fallback = icon.getAttribute('data-lucide-fallback') || 'circle';
            icon.setAttribute('data-lucide', safeIconName(icon.getAttribute('data-lucide'), fallback));
        });
    }

    function render(root) {
        normalizeDataLucide(root);
        if (global.lucide && typeof global.lucide.createIcons === 'function') {
            global.lucide.createIcons();
        }
    }

    global.AncoreIcons = {
        legacyMap: LEGACY_ICON_MAP,
        normalize: normalizeIconName,
        safeName: safeIconName,
        html: iconHtml,
        create: createIcon,
        render,
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => render(document), { once: true });
    } else {
        render(document);
    }
})(typeof window !== 'undefined' ? window : globalThis);
