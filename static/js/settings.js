(function () {
    'use strict';

    let cleanup = () => {};

    function initializeSettings() {
        cleanup();
        cleanup = () => {};
        const page = document.querySelector('[data-settings-center]');
        if (!page) return;
        const controller = new AbortController();
        const on = (target, event, callback) => target.addEventListener(event, callback, { signal: controller.signal });
        cleanup = () => controller.abort();
        const status = page.querySelector('[data-settings-status]');
        const summary = page.querySelector('[data-settings-account-summary]');
        const categories = Array.from(page.querySelectorAll('[data-settings-category]'));
        const groups = Array.from(page.querySelectorAll('[data-settings-group]'), (element) => ({
            element,
            category: element.dataset.settingsGroup,
            rowCount: element.querySelectorAll('[data-settings-row]').length,
        }));
        const hashCategories = {
            account: 'account', security: 'account', workspace: 'workspace',
            preferences: 'preferences', appearance: 'preferences',
            notifications: 'preferences', region: 'preferences',
        };
        let category = hashCategories[window.location.hash.slice(1)] || 'all';

        function filterSettings(announce = true) {
            let count = 0;
            groups.forEach((group) => {
                const visible = category === 'all' || category === group.category;
                group.element.hidden = !visible;
                if (visible) count += group.rowCount;
            });
            categories.forEach((link) => {
                const active = link.dataset.settingsCategory === category;
                link.classList.toggle('is-active', active);
                if (active) link.setAttribute('aria-current', 'true');
                else link.removeAttribute('aria-current');
            });
            summary.hidden = !['all', 'account'].includes(category);
            if (announce) status.textContent = `Liczba widocznych ustawień: ${count}.`;
        }

        categories.forEach((link) => on(link, 'click', (event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            category = link.dataset.settingsCategory;
            const hash = category === 'all' ? '' : `#${category}`;
            window.history.pushState(null, '', `${window.location.pathname}${window.location.search}${hash}`);
            filterSettings();
        }));
        on(window, 'hashchange', () => {
            category = hashCategories[window.location.hash.slice(1)] || 'all';
            filterSettings();
        });

        const sidebarSwitch = page.querySelector('[data-settings-sidebar-switch]');
        const sidebarToggle = document.querySelector('[data-sidebar-collapse-toggle]');
        const mobile = window.matchMedia('(max-width: 767px)');
        function syncSidebarSwitch() {
            sidebarSwitch.checked = document.documentElement.classList.contains('sidebar-collapsed');
            sidebarSwitch.disabled = mobile.matches || !sidebarToggle;
        }
        on(sidebarSwitch, 'change', () => {
            if (sidebarToggle && !mobile.matches) sidebarToggle.click();
            syncSidebarSwitch();
            status.textContent = sidebarSwitch.checked ? 'Menu boczne zostało zwinięte.' : 'Menu boczne zostało rozwinięte.';
        });
        // Delegate persistence to the shell and keep both controls synchronized.
        const sidebarObserver = new MutationObserver(syncSidebarSwitch);
        sidebarObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
        on(mobile, 'change', syncSidebarSwitch);
        cleanup = () => { controller.abort(); sidebarObserver.disconnect(); };
        syncSidebarSwitch();

        on(page.querySelector('[data-settings-notifications]'), 'click', (event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            const toggle = document.querySelector('[data-notifications-toggle]');
            if (!toggle) return;
            event.preventDefault();
            toggle.click();
        });
        filterSettings(false);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeSettings, { once: true });
    else initializeSettings();
    document.addEventListener('ancore:content-loaded', initializeSettings);
})();
