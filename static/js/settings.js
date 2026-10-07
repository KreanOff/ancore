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
        const categories = Array.from(document.querySelectorAll('[data-sidebar-navigation="settings"] [data-settings-category]'));
        const groups = Array.from(page.querySelectorAll('[data-settings-group]'), (element) => ({
            element,
            category: element.dataset.settingsGroup,
            rowCount: element.querySelectorAll('[data-settings-row]').length,
        }));
        const hashCategories = {
            account: 'account', security: 'account', workspace: 'workspace',
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
                link.classList.toggle('active', active);
                if (active) link.setAttribute('aria-current', 'page');
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
            const url = `${window.location.pathname}${window.location.search}${hash}`;
            if (url !== `${window.location.pathname}${window.location.search}${window.location.hash}`) {
                window.history.pushState({ ...window.history.state }, '', url);
            }
            filterSettings();
            page.querySelector('.settings-scroll-area').scrollTo({ top: 0 });
        }));
        on(window, 'hashchange', () => {
            category = hashCategories[window.location.hash.slice(1)] || 'all';
            filterSettings();
        });

        filterSettings(false);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeSettings, { once: true });
    else initializeSettings();
    document.addEventListener('ancore:content-loaded', initializeSettings);
    document.addEventListener('ancore:content-unloading', () => cleanup());
})();
