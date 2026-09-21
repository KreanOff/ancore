(function () {
    if (window.AncoreDropdownLayer) return;
    // Keep the menu in its form for delegated events, labels and modal focus traps.
    // The browser's top layer lets it escape scrolling containers and their footers.
    let active = null;
    let frame = null;

    // Existing searchable pickers keep their own filtering (including remote
    // company/person lookups). Add the same search UI to the remaining choices.
    function addModalSearch(menu, anchor) {
        if (!anchor.closest('.tasks-modal, .profile-edit-dialog') || menu.querySelector('input:not([type="hidden"])')) return null;

        const options = Array.from(menu.querySelectorAll('button'));
        const originalHidden = options.map(option => option.hidden);
        const searchRow = document.createElement('div');
        searchRow.className = 'ancore-custom-select__search';
        const icon = document.createElement('i');
        icon.setAttribute('data-icon', 'search');
        icon.setAttribute('aria-hidden', 'true');
        const input = document.createElement('input');
        input.type = 'search';
        input.className = 'ancore-custom-select__search-input';
        input.placeholder = 'Szukaj';
        input.setAttribute('aria-label', 'Szukaj na liście');
        input.setAttribute('data-dropdown-search', '');
        input.autocomplete = 'off';
        input.spellcheck = false;
        searchRow.append(icon, input);
        const empty = document.createElement('span');
        empty.className = 'ancore-custom-select__empty';
        empty.textContent = 'Brak wyników';
        empty.setAttribute('role', 'status');
        empty.hidden = options.some(option => !option.hidden);
        menu.prepend(searchRow);
        menu.append(empty);
        menu.setAttribute('data-dropdown-searchable', '');
        window.AncoreIcons?.render(searchRow);

        const normalize = text => text.toLocaleLowerCase('pl').normalize('NFD').replace(/\p{Diacritic}/gu, '').replace(/ł/g, 'l').trim();
        input.addEventListener('input', () => {
            const query = normalize(input.value);
            options.forEach((option, index) => {
                option.hidden = originalHidden[index] || !normalize(option.textContent).includes(query);
            });
            empty.hidden = options.some(option => !option.hidden);
            menu.scrollTop = 0;
            schedulePosition();
        });

        function handleKeydown(event) {
            if (event.isComposing) return;
            const visible = options.filter(option => !option.hidden && !option.disabled);
            const inSearch = event.target === input;
            const index = visible.indexOf(event.target);
            if (!inSearch && index < 0) return;
            if (inSearch && (event.key === 'Home' || event.key === 'End')) {
                event.stopPropagation();
                return;
            }
            if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
                event.preventDefault();
                event.stopPropagation();
                if (!visible.length) return;
                const next = event.key === 'Home' ? 0 : event.key === 'End' ? visible.length - 1
                    : inSearch ? (event.key === 'ArrowDown' ? 0 : visible.length - 1)
                        : (index + (event.key === 'ArrowDown' ? 1 : -1) + visible.length) % visible.length;
                visible[next]?.focus({ preventScroll: true });
                visible[next]?.scrollIntoView({ block: 'nearest' });
            } else if (event.key === 'Enter' || (!inSearch && event.key === ' ')) {
                event.preventDefault();
                event.stopPropagation();
                (inSearch ? visible[0] : visible[index])?.click();
            }
        }
        menu.addEventListener('keydown', handleKeydown, true);
        return {
            input,
            remove() {
                menu.removeEventListener('keydown', handleKeydown, true);
                options.forEach((option, index) => { option.hidden = originalHidden[index]; });
                searchRow.remove();
                empty.remove();
                menu.removeAttribute('data-dropdown-searchable');
            }
        };
    }

    function hide(menu) {
        if (!active || active.menu !== menu) return;
        const current = active;
        active = null;
        cancelAnimationFrame(frame);
        frame = null;
        current.observer.disconnect();
        current.resizeObserver.disconnect();
        current.search?.remove();
        if (menu.matches(':popover-open')) menu.hidePopover();
        menu.removeAttribute('popover');
        menu.classList.remove('ancore-dropdown-layer');
        ['width', 'height', 'left', 'top'].forEach(name => menu.style.removeProperty(`--dropdown-layer-${name}`));
    }

    function dismiss(restoreFocus = false) {
        if (!active) return;
        const { menu, anchor, onClose } = active;
        hide(menu);
        onClose();
        if (restoreFocus && anchor.isConnected) anchor.focus({ preventScroll: true });
    }

    function isVisible(element) {
        return element.isConnected && element.getClientRects().length > 0
            && !element.closest('[hidden], [inert], [aria-hidden="true"]')
            && getComputedStyle(element).visibility !== 'hidden';
    }

    function anchorIsClipped(anchor, rect) {
        for (let parent = anchor.parentElement; parent; parent = parent.parentElement) {
            const style = getComputedStyle(parent);
            const bounds = parent.getBoundingClientRect();
            if (/(auto|scroll|hidden|clip)/.test(style.overflowY)
                && (rect.bottom <= bounds.top || rect.top >= bounds.bottom)) return true;
            if (/(auto|scroll|hidden|clip)/.test(style.overflowX)
                && (rect.right <= bounds.left || rect.left >= bounds.right)) return true;
        }
        return false;
    }

    function position() {
        frame = null;
        if (!active) return;
        const { menu, anchor, maxHeight } = active;
        if (!isVisible(anchor) || !isVisible(menu) || anchor.getAttribute('aria-expanded') === 'false') {
            dismiss();
            return;
        }

        const rect = anchor.getBoundingClientRect();
        if (anchorIsClipped(anchor, rect)) {
            dismiss();
            return;
        }
        const scale = anchor.currentCSSZoom || rect.width / anchor.offsetWidth || 1;
        const viewport = window.visualViewport;
        const leftEdge = (viewport?.offsetLeft || 0) + 8;
        const topEdge = (viewport?.offsetTop || 0) + 8;
        const rightEdge = (viewport?.offsetLeft || 0) + (viewport?.width || innerWidth) - 8;
        const bottomEdge = (viewport?.offsetTop || 0) + (viewport?.height || innerHeight) - 8;
        const gap = 4 * scale;
        const desiredWidth = rect.width / scale;
        menu.style.setProperty('--dropdown-layer-width', `${Math.min(desiredWidth, (rightEdge - leftEdge) / scale)}px`);

        const desiredHeight = Math.min(maxHeight, menu.scrollHeight + menu.offsetHeight - menu.clientHeight) * scale;
        const below = Math.max(0, bottomEdge - rect.bottom - gap);
        const above = Math.max(0, rect.top - topEdge - gap);
        const openAbove = desiredHeight > below && above > below;
        menu.style.setProperty('--dropdown-layer-height', `${Math.min(maxHeight, (openAbove ? above : below) / scale)}px`);
        const bounds = menu.getBoundingClientRect();
        const left = Math.max(leftEdge, Math.min(rect.left, rightEdge - bounds.width));
        const top = Math.max(topEdge, Math.min(openAbove ? rect.top - gap - bounds.height : rect.bottom + gap, bottomEdge - bounds.height));
        menu.style.setProperty('--dropdown-layer-left', `${left / scale}px`);
        menu.style.setProperty('--dropdown-layer-top', `${top / scale}px`);
    }

    function schedulePosition() {
        if (active && frame === null) frame = requestAnimationFrame(position);
    }

    function open(menu, anchor, onClose) {
        if (!menu || !anchor || typeof menu.showPopover !== 'function') return;
        // Company/responsible editors also have intentionally inline panels.
        if (menu.matches('.tasks-company-select__panel, .tasks-responsible-select__panel')) return;
        if (active?.menu === menu) {
            schedulePosition();
            return;
        }
        dismiss();
        const search = addModalSearch(menu, anchor);
        const scale = anchor.currentCSSZoom || anchor.getBoundingClientRect().width / anchor.offsetWidth || 1;
        const width = anchor.getBoundingClientRect().width / scale;
        const maxHeight = parseFloat(getComputedStyle(menu).maxHeight) || Infinity;
        const observer = new MutationObserver(() => {
            if (!isVisible(anchor) || menu.hidden || anchor.getAttribute('aria-expanded') === 'false') dismiss();
            else schedulePosition();
        });
        const resizeObserver = new ResizeObserver(schedulePosition);
        active = { menu, anchor, onClose, maxHeight, observer, resizeObserver, search };
        menu.style.setProperty('--dropdown-layer-width', `${width}px`);
        menu.classList.add('ancore-dropdown-layer');
        menu.setAttribute('popover', 'manual');
        menu.showPopover();
        position();

        for (let element = anchor; element; element = element.parentElement) {
            observer.observe(element, { attributes: true, attributeFilter: ['class', 'hidden', 'aria-hidden', 'aria-expanded', 'inert', 'style'] });
        }
        observer.observe(menu, { attributes: true, attributeFilter: ['hidden', 'class'], childList: true, subtree: true });
        observer.observe(document.body, { childList: true, subtree: true });
        resizeObserver.observe(anchor);
        resizeObserver.observe(menu);
        if (active?.menu === menu) search?.input.focus({ preventScroll: true });
    }

    window.AncoreDropdownLayer = { open, hide, dismiss };
    window.addEventListener('keydown', event => {
        if (event.key !== 'Escape' || !active) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        dismiss(true);
    }, true);
    document.addEventListener('pointerdown', event => {
        if (active && !active.menu.contains(event.target) && !active.anchor.contains(event.target)) dismiss();
    }, true);
    document.addEventListener('focusin', event => {
        if (active && !active.menu.contains(event.target) && !active.anchor.contains(event.target)) dismiss();
    });
    document.addEventListener('scroll', event => {
        if (active && !active.menu.contains(event.target)) schedulePosition();
    }, true);
    window.addEventListener('resize', schedulePosition);
    window.visualViewport?.addEventListener('resize', schedulePosition);
    window.visualViewport?.addEventListener('scroll', schedulePosition);
    document.addEventListener('ancore:content-loaded', () => dismiss());
    window.addEventListener('pagehide', () => dismiss());
})();
