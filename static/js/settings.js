(function () {
    'use strict';

    let cleanup = () => {};

    function initializeSpacesDirectory(page) {
        const controller = new AbortController();
        const on = (target, event, callback) => target.addEventListener(event, callback, { signal: controller.signal });
        const selectAll = page.querySelector('[data-settings-spaces-select-all]');
        const editButton = page.querySelector('[data-settings-spaces-edit]');
        const deleteButton = page.querySelector('[data-settings-spaces-delete]');
        const selected = () => Array.from(page.querySelectorAll('[data-settings-spaces-select]'));
        function selectedRow() {
            const boxes = selected().filter((box) => box.checked);
            return boxes.length === 1 ? boxes[0].closest('[data-settings-spaces-row]') : null;
        }
        function syncSelection() {
            const boxes = selected();
            const count = boxes.filter((box) => box.checked).length;
            if (selectAll) {
                selectAll.checked = boxes.length > 0 && count === boxes.length;
                selectAll.indeterminate = count > 0 && count < boxes.length;
            }
            boxes.forEach((box) => box.closest('[data-settings-spaces-row]').classList.toggle('checked', box.checked));
            const row = selectedRow();
            [[editButton, row?.dataset.settingsSpaceEditUrl], [deleteButton, row?.dataset.settingsSpaceDeleteUrl]].forEach(([button, url]) => {
                if (!button) return;
                button.disabled = !url;
                button.title = count !== 1 ? 'Zaznacz jedną przestrzeń.' : !url ? 'Nie masz uprawnień do zarządzania tą przestrzenią.' : '';
            });
        }
        on(page, 'change', (event) => {
            if (event.target === selectAll) selected().forEach((box) => { box.checked = selectAll.checked; });
            if (event.target.matches('[data-settings-spaces-select], [data-settings-spaces-select-all]')) syncSelection();
        });
        function openUrl(url) {
            if (!url) return;
            if (window.AncoreApp?.canNavigatePartially?.(url)) window.AncoreApp.navigate(url);
            else window.location.assign(url);
        }
        if (editButton) on(editButton, 'click', () => openUrl(selectedRow()?.dataset.settingsSpaceEditUrl));
        if (deleteButton) on(deleteButton, 'click', () => openUrl(selectedRow()?.dataset.settingsSpaceDeleteUrl));
        on(page, 'click', (event) => {
            if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            if (event.target.closest('a,button,input,label,select,textarea') || window.getSelection()?.toString()) return;
            const row = event.target.closest('[data-settings-spaces-row]');
            if (row && event.target.closest('[data-column="select"]')) {
                row.querySelector('[data-settings-spaces-select]').click();
                return;
            }
            if (row) openUrl(row.dataset.settingsSpaceUrl);
        });
        on(page, 'keydown', (event) => {
            if (!event.target.matches('[data-settings-spaces-row]') || !['Enter', ' '].includes(event.key)) return;
            event.preventDefault();
            openUrl(event.target.dataset.settingsSpaceUrl);
        });
        syncSelection();
        return () => controller.abort();
    }

    function initializeSettings() {
        cleanup();
        cleanup = () => {};
        if (document.querySelector('[data-react-root="page"]')) return;
        const spacesDirectory = document.querySelector('[data-settings-spaces-directory]');
        if (spacesDirectory) {
            cleanup = initializeSpacesDirectory(spacesDirectory);
            return;
        }
        const page = document.querySelector('[data-settings-center]');
        if (!page) return;
        const workspaceLink = document.querySelector('[data-sidebar-navigation="settings"] [data-settings-category="workspace"]');
        function openWorkspace() {
            if (window.location.hash !== '#workspace' || !workspaceLink) return false;
            window.location.replace(workspaceLink.href);
            return true;
        }
        if (openWorkspace()) return;
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
        const defaultCategory = page.dataset.settingsSection === 'spaces' ? 'spaces' : 'all';
        let category = hashCategories[window.location.hash.slice(1)] || defaultCategory;

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
            if (summary) summary.hidden = !['all', 'account'].includes(category);
            if (announce) status.textContent = `Liczba widocznych ustawień: ${count}.`;
        }

        categories.forEach((link) => on(link, 'click', (event) => {
            if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            if (link.pathname !== window.location.pathname || link.search !== window.location.search) return;
            if (link.dataset.settingsCategory === 'spaces') return;
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
        function syncCategory() {
            if (openWorkspace()) return;
            category = hashCategories[window.location.hash.slice(1)] || defaultCategory;
            filterSettings();
        }
        on(window, 'hashchange', syncCategory);
        on(window, 'popstate', syncCategory);

        filterSettings(false);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeSettings, { once: true });
    else initializeSettings();
    document.addEventListener('ancore:content-loaded', initializeSettings);
    document.addEventListener('ancore:content-unloading', () => cleanup());
})();
