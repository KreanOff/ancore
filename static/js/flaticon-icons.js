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

    const ICON_ALIASES = {
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

    const catalog = global.AncoreFlaticon;
    const owns = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

    function normalizeIconName(name, fallback) {
        const raw = String(name || '').trim();
        if (!raw) return fallback || 'circle';
        if (owns(LEGACY_ICON_MAP, raw)) return LEGACY_ICON_MAP[raw];
        const kebab = raw
            .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
            .replace(/_/g, '-')
            .replace(/\s+/g, '-')
            .replace(/[^a-zA-Z0-9-]/g, '')
            .replace(/-+/g, '-')
            .replace(/^-|-$/g, '')
            .toLowerCase();
        const alias = kebab.replace(/-/g, '');
        return (owns(ICON_ALIASES, alias) ? ICON_ALIASES[alias] : kebab) || fallback || 'circle';
    }

    function flaticonName(name) {
        return owns(catalog.aliases, name) ? catalog.aliases[name] : name;
    }

    function safeIconName(name, fallback) {
        const normalized = normalizeIconName(name, fallback);
        if (owns(catalog.icons, flaticonName(normalized))) return normalized;
        const defaultName = normalizeIconName(fallback, 'circle');
        return owns(catalog.icons, flaticonName(defaultName)) ? defaultName : 'circle';
    }

    function createIcon(name, options) {
        const opts = options || {};
        const icon = document.createElement('i');
        icon.setAttribute('data-icon', safeIconName(name, opts.fallback));
        if (opts.className) icon.className = opts.className;
        if (opts.label) {
            icon.setAttribute('aria-label', opts.label);
            icon.setAttribute('role', 'img');
        } else {
            icon.setAttribute('aria-hidden', 'true');
        }
        if (opts.title) icon.setAttribute('title', opts.title);
        return icon;
    }

    function iconHtml(name, options) {
        return createIcon(name, options).outerHTML;
    }

    function render(root) {
        const scope = root && root.querySelectorAll ? root : document;
        const placeholders = Array.from(scope.querySelectorAll('[data-icon]'));
        if (scope.matches?.('[data-icon]')) placeholders.unshift(scope);
        placeholders.forEach(icon => {
            const name = safeIconName(icon.getAttribute('data-icon'), icon.getAttribute('data-icon-fallback'));
            const source = flaticonName(name);
            if (icon.localName === 'svg' && icon.getAttribute('data-flaticon') === source) return;
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            Array.from(icon.attributes).forEach(attribute => {
                if (!['stroke', 'stroke-width', 'fill', 'viewBox', 'data-icon-fallback'].includes(attribute.name)) {
                    svg.setAttribute(attribute.name, attribute.value);
                }
            });
            svg.classList.add('ancore-icon');
            svg.setAttribute('data-icon', name);
            svg.setAttribute('data-flaticon', source);
            svg.setAttribute('viewBox', '0 0 24 24');
            svg.setAttribute('width', icon.getAttribute('width') || '24');
            svg.setAttribute('height', icon.getAttribute('height') || '24');
            svg.setAttribute('fill', 'currentColor');
            svg.setAttribute('stroke', 'none');
            svg.setAttribute('focusable', 'false');
            if (svg.hasAttribute('aria-label')) {
                svg.setAttribute('role', 'img');
            } else if (!svg.hasAttribute('aria-labelledby')) {
                svg.setAttribute('aria-hidden', 'true');
            }
            if (icon.getAttribute('title')) {
                const title = document.createElementNS(svg.namespaceURI, 'title');
                title.textContent = icon.getAttribute('title');
                svg.appendChild(title);
            }
            const path = document.createElementNS(svg.namespaceURI, 'path');
            path.setAttribute('d', catalog.icons[source]);
            svg.appendChild(path);
            icon.replaceWith(svg);
        });
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
    document.addEventListener('ancore:content-loaded', () => render(document));
})(typeof window !== 'undefined' ? window : globalThis);
