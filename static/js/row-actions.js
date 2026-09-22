/* Shared catalogue action menus: Documents and Workspace teams. */
(function () {
    let controller;
    function init() {
        controller?.abort();
        controller = new AbortController();
        initRowActionMenus({ signal: controller.signal });
    }
    function initRowActionMenus(options) {
        const menus = [...document.querySelectorAll('[data-row-actions], [data-document-actions]')];
        if (!menus.length) return;

        function closeMenus() {
            menus.forEach(menu => {
                const panel = menu.querySelector('[data-row-actions-panel], [data-document-actions-panel]');
                if (panel.matches(':popover-open')) panel.hidePopover();
            });
        }

        menus.forEach(menu => {
            const toggle = menu.querySelector('[data-row-actions-toggle], [data-document-actions-toggle]');
            const panel = menu.querySelector('[data-row-actions-panel], [data-document-actions-panel]');
            const items = [...panel.querySelectorAll('a[href], button:not(:disabled)')];
            // Reinitialization after partial navigation must not leave a stale open menu.
            if (panel.matches(':popover-open')) panel.hidePopover();
            toggle.setAttribute('aria-expanded', 'false');

            function position() {
                const anchor = toggle.getBoundingClientRect();
                const scale = anchor.width / toggle.offsetWidth || 1;
                const bounds = panel.getBoundingClientRect();
                const gap = 6;
                const margin = 8;
                const left = Math.max(margin, Math.min(anchor.left, window.innerWidth - bounds.width - margin));
                const top = anchor.bottom + gap + bounds.height <= window.innerHeight - margin
                    ? anchor.bottom + gap : Math.max(margin, anchor.top - bounds.height - gap);
                panel.style.left = `${left / scale}px`;
                panel.style.top = `${top / scale}px`;
            }

            toggle.addEventListener('click', event => {
                event.preventDefault();
                if (panel.matches(':popover-open')) panel.hidePopover();
                else {
                    panel.showPopover();
                    position();
                    // Only keyboard/assistive activation moves focus into the menu.
                    if (event.detail === 0) items[0]?.focus({ preventScroll: true });
                }
            }, options);
            panel.addEventListener('beforetoggle', event => {
                toggle.setAttribute('aria-expanded', String(event.newState === 'open'));
            }, options);
            menu.addEventListener('keydown', event => {
                if (event.key === 'Escape' && panel.matches(':popover-open')) {
                    event.preventDefault();
                    event.stopPropagation();
                    panel.hidePopover();
                    toggle.focus({ preventScroll: true });
                    return;
                }
                if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
                event.preventDefault();
                if (!panel.matches(':popover-open')) {
                    panel.showPopover();
                    position();
                }
                const current = items.indexOf(document.activeElement);
                const index = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1
                    : current === -1 ? (event.key === 'ArrowDown' ? 0 : items.length - 1)
                    : (current + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
                items[index]?.focus({ preventScroll: true });
            }, options);
            panel.addEventListener('click', event => {
                if (event.target.closest('a, button')) {
                    panel.hidePopover();
                    toggle.focus({ preventScroll: true });
                }
            }, options);
            menu.addEventListener('focusout', event => {
                if (event.relatedTarget && !menu.contains(event.relatedTarget) && panel.matches(':popover-open')) {
                    panel.hidePopover();
                }
            }, options);
        });
        window.addEventListener('resize', closeMenus, options);
        document.addEventListener('scroll', event => {
            if (!event.target.closest?.('[data-row-actions-panel], [data-document-actions-panel]')) closeMenus();
        }, { ...options, capture: true });
        options.signal.addEventListener('abort', closeMenus, { once: true });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
