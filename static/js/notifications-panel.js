(function () {
    if (window.AncoreNotificationCenter) return;
    const panel = document.querySelector('[data-notifications-panel]');
    const toggle = document.querySelector('[data-notifications-toggle]');
    if (!panel || !toggle) return;
    const controllers = new Map();
    let summaryRequest = null;
    let refreshTimer = null;
    let revision = null;
    let previousUnread = null;
    let inertElements = [];
    const isOpen = () => panel.classList.contains('is-open');
    const icons = scope => window.AncoreIcons?.render(scope);

    function closeActionMenus() {
        panel.querySelectorAll('[data-row-actions-panel]:popover-open').forEach(menu => menu.hidePopover());
    }

    function updateSummary(payload) {
        const unread = Number(payload.unread_count);
        if (!Number.isInteger(unread)) return;
        const label = `Nieprzeczytane: ${unread}.`;
        const indicator = document.querySelector('[data-notifications-pending]');
        if (indicator) indicator.hidden = unread === 0;
        const summaryStatus = document.querySelector('[data-notifications-unread-status]');
        if (summaryStatus) summaryStatus.textContent = label;
        toggle.title = `Powiadomienia · ${label}`;
        document.querySelectorAll('[data-notifications-unread-count]').forEach(node => {
            node.textContent = String(unread);
        });
        const nextRevision = JSON.stringify(payload.revision);
        if (revision !== null && (revision !== nextRevision || previousUnread !== unread)) {
            controllers.forEach((controller, root) => {
                if (!root.hidden && root.getAttribute('aria-hidden') !== 'true' && controller.loaded) root.querySelector('[data-notification-new-items]').hidden = false;
            });
        }
        revision = nextRevision;
        previousUnread = unread;
    }

    async function refreshSummary() {
        if (document.hidden || summaryRequest) return;
        const request = new AbortController();
        summaryRequest = request;
        const timeout = setTimeout(() => request.abort(), 10000);
        try {
            const url = new URL(panel.dataset.notificationsUrl, location.href);
            url.searchParams.set('summary', '1');
            const response = await fetch(url, { cache: 'no-store', credentials: 'same-origin', signal: request.signal });
            if (response.ok && summaryRequest === request) updateSummary(await response.json());
        } catch (_) {
            // Keep the last known badge offline. The center offers an explicit retry.
        } finally {
            clearTimeout(timeout);
            if (summaryRequest === request) summaryRequest = null;
        }
    }

    function scheduleRefresh() {
        clearTimeout(refreshTimer);
        if (!document.hidden) refreshTimer = setTimeout(async () => {
            await refreshSummary();
            scheduleRefresh();
        }, 30000);
    }

    function makeController(root) {
        const content = root.querySelector('[data-notifications-content]');
        const status = root.querySelector('[data-notifications-status]');
        const error = root.querySelector('[data-notification-error]');
        const more = root.querySelector('[data-notification-more]');
        const pagination = root.querySelector('[data-notification-pagination]');
        const readAll = root.querySelector('[data-notification-read-all]');
        const deleteAll = root.querySelector('[data-notification-delete-all]');
        let request = null;
        let mutating = false;
        let deletable = 0;
        let cursor = root.dataset.nextCursor || '';
        let snapshot = root.dataset.snapshot || '';
        let view = root.querySelector('[data-notification-filter][aria-pressed="true"]')?.dataset.notificationFilter || 'all';
        const controller = { loaded: Boolean(snapshot), load, abort: () => request?.abort() };

        function reportError(message) {
            error.textContent = message;
            error.hidden = false;
            status.textContent = message;
        }

        async function load({ append = false, quiet = false, focusKey = '' } = {}) {
            closeActionMenus();
            request?.abort();
            request = new AbortController();
            const activeRequest = request;
            let timedOut = false;
            const timeout = setTimeout(() => { timedOut = true; activeRequest.abort(); }, 20000);
            error.hidden = true;
            content.setAttribute('aria-busy', 'true');
            readAll.disabled = true;
            deleteAll.disabled = true;
            more.disabled = true;
            const scrollTop = content.scrollTop;
            if (!append && !quiet) {
                content.innerHTML = '<div class="global-search-loading" aria-hidden="true">' + '<span class="global-search-loading__row"><span></span><span></span></span>'.repeat(5) + '</div>';
                pagination.hidden = true;
            }
            status.textContent = 'Pobieranie powiadomień…';
            const url = new URL(root.dataset.notificationsUrl, location.href);
            url.searchParams.set('view', view);
            url.searchParams.set('workspace', root.querySelector('[data-notification-workspace]').value);
            if (append && cursor) url.searchParams.set('cursor', cursor);
            try {
                const response = await fetch(url, {
                    credentials: 'same-origin', cache: 'no-store', signal: activeRequest.signal,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!response.ok) throw new Error('load');
                const payload = await response.json();
                if (request !== activeRequest) return;
                updateSummary(payload);
                if (append) {
                    const template = document.createElement('template');
                    template.innerHTML = payload.html;
                    const list = content.querySelector('[data-notification-list]');
                    const incoming = template.content.querySelector('[data-notification-list]');
                    const lastGroup = Array.from(list.querySelectorAll('.notifications-group-label')).pop();
                    const firstGroup = incoming.querySelector('.notifications-group-label');
                    if (lastGroup?.textContent === firstGroup?.textContent) firstGroup?.remove();
                    const firstNew = incoming.querySelector('[data-notification-open]');
                    list.append(...incoming.childNodes);
                    firstNew?.focus({ preventScroll: true });
                } else {
                    content.innerHTML = payload.html;
                    content.scrollTop = quiet ? scrollTop : 0;
                }
                cursor = payload.next_cursor;
                snapshot = payload.snapshot;
                controller.loaded = true;
                deletable = payload.deletable_count;
                readAll.disabled = payload.filtered_unread_count === 0;
                readAll.title = payload.filtered_unread_count === 0
                    ? 'Wszystkie powiadomienia w tym widoku są przeczytane'
                    : 'Oznacz wszystkie powiadomienia z wybranego filtra jako przeczytane, również starsze';
                deleteAll.disabled = deletable === 0;
                pagination.hidden = !cursor;
                root.querySelector('[data-notification-progress]').textContent = `${content.querySelectorAll('[data-notification-item]').length} z ${payload.total}`;
                root.querySelector('[data-notification-new-items]').hidden = true;
                status.textContent = `Powiadomienia: ${payload.total}. Nieprzeczytane: ${payload.filtered_unread_count}.`;
                icons(content);
                document.dispatchEvent(new CustomEvent('ancore:notifications-loaded'));
                if (focusKey) {
                    const row = Array.from(content.querySelectorAll('[data-notification-item]')).find(item => item.dataset.notificationKey === focusKey);
                    (row?.querySelector('[data-row-actions-toggle]') || content).focus({ preventScroll: true });
                }
                return true;
            } catch (failure) {
                if ((failure.name === 'AbortError' && !timedOut) || request !== activeRequest) return;
                if (!quiet && !append) content.innerHTML = '<div class="global-search-state notifications-panel__state"><span class="global-search-state__icon"><i data-icon="wifi-off" aria-hidden="true"></i></span><h3>Nie udało się pobrać powiadomień</h3><p>Sprawdź połączenie i spróbuj ponownie.</p><button type="button" class="global-search-state__retry" data-notification-refresh>Spróbuj ponownie</button></div>';
                else reportError('Nie udało się odświeżyć listy. Użyj przycisku odświeżania, aby spróbować ponownie.');
                status.textContent = 'Nie udało się pobrać powiadomień.';
                icons(content);
            } finally {
                clearTimeout(timeout);
                if (request === activeRequest) {
                    content.setAttribute('aria-busy', 'false');
                    more.disabled = false;
                }
            }
        }

        async function mutate(action, key = '', link = null, actionSnapshot = snapshot) {
            if (mutating) return;
            closeActionMenus();
            mutating = true;
            error.hidden = true;
            request?.abort();
            summaryRequest?.abort();
            summaryRequest = null;
            const buttons = root.querySelectorAll('[data-notification-action], [data-row-actions-toggle], [data-notification-read-all], [data-notification-delete-all]');
            const previousDisabled = new Map(Array.from(buttons, button => [button, button.disabled]));
            const restoreButtons = () => previousDisabled.forEach((disabled, button) => {
                if (button.isConnected) button.disabled = disabled;
            });
            buttons.forEach(button => { button.disabled = true; });
            const mutationRequest = new AbortController();
            const timeout = setTimeout(() => mutationRequest.abort(), 15000);
            try {
                const body = new URLSearchParams({ action, key, snapshot: actionSnapshot });
                const response = await fetch(root.dataset.notificationsActionUrl, {
                    method: 'POST', credentials: 'same-origin', signal: mutationRequest.signal,
                    headers: { 'X-CSRFToken': root.querySelector('[name=csrfmiddlewaretoken]').value, 'X-Requested-With': 'XMLHttpRequest' }, body,
                });
                const payload = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(payload.error || 'Nie udało się zapisać zmiany. Spróbuj ponownie.');
                updateSummary(payload);
                if (link) {
                    setOpen(false);
                    if (window.AncoreApp?.canNavigatePartially(link.href)) window.AncoreApp.navigate(link.href);
                    else window.location.assign(link.href);
                } else {
                    const refreshed = await load({ quiet: true, focusKey: key });
                    const message = {
                        archive: 'Powiadomienie przeniesione do archiwum.',
                        restore: 'Powiadomienie przywrócone.',
                        delete: 'Powiadomienie usunięte.',
                        delete_all: 'Powiadomienia z wybranego widoku zostały usunięte.',
                        read_all: 'Powiadomienia z wybranego widoku oznaczono jako przeczytane.',
                    }[action] || 'Stan powiadomień zapisany.';
                    if (refreshed) status.textContent = message;
                    else restoreButtons();
                    if (['read_all', 'delete', 'delete_all'].includes(action)) window.showNotification?.(message, 'success');
                }
            } catch (failure) {
                reportError(failure.name === 'AbortError' || failure instanceof TypeError ? 'Brak połączenia. Zmiana nie została potwierdzona — spróbuj ponownie.' : failure.message);
                restoreButtons();
            } finally {
                clearTimeout(timeout);
                mutating = false;
            }
        }

        function confirmDelete(action, key = '') {
            if (mutating || document.querySelector('.confirm-modal-overlay')) return;
            const actionSnapshot = snapshot;
            window.showConfirmModal({
                title: action === 'delete_all' ? 'Usunąć wszystkie powiadomienia?' : 'Usunąć powiadomienie?',
                message: (action === 'delete_all'
                    ? `Usuniesz powiadomienia z wybranego widoku (${deletable}), również ze starszych stron. `
                    : 'Usuniesz to powiadomienie ze swojej listy. ')
                    + 'Usuniętych powiadomień nie można przywrócić. Historia zadań pozostanie bez zmian.',
                confirmText: action === 'delete_all' ? 'Usuń wszystkie' : 'Usuń',
                onConfirm: () => mutate(action, key, null, actionSnapshot),
            });
        }

        root.addEventListener('click', event => {
            if (mutating) return;
            const filter = event.target.closest('[data-notification-filter]');
            if (filter) {
                view = filter.dataset.notificationFilter;
                root.querySelectorAll('[data-notification-filter]').forEach(button => button.setAttribute('aria-pressed', String(button === filter)));
                load();
            } else if (event.target.closest('[data-notification-refresh], [data-notification-new-items]')) load();
            else if (event.target.closest('[data-notification-more]')) load({ append: true });
            else if (event.target.closest('[data-notification-read-all]')) mutate('read_all');
            else if (event.target.closest('[data-notification-delete-all]')) confirmDelete('delete_all');
            else if (event.target.closest('[data-notification-action]')) {
                const button = event.target.closest('[data-notification-action]');
                const key = button.closest('[data-notification-item]').dataset.notificationKey;
                if (button.dataset.notificationAction === 'delete') confirmDelete('delete', key);
                else mutate(button.dataset.notificationAction, key);
            } else {
                const link = event.target.closest('[data-notification-open]');
                if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
                    event.preventDefault();
                    mutate('read', link.closest('[data-notification-item]').dataset.notificationKey, link);
                }
            }
        });
        root.querySelector('[data-notification-workspace]').addEventListener('change', () => load());
        return controller;
    }

    function init() {
        controllers.forEach((controller, root) => {
            if (!root.isConnected) { controller.abort(); controllers.delete(root); }
        });
        document.querySelectorAll('[data-notifications-center]').forEach(root => {
            if (!controllers.has(root)) controllers.set(root, makeController(root));
        });
    }

    function setOpen(open) {
        if (open === isOpen()) return;
        if (open) {
            window.dispatchEvent(new CustomEvent('ancore:notifications-open'));
            window.AncoreTaskModals.open(panel, panel.querySelector('[data-notifications-close]'));
        } else {
            window.AncoreTaskModals.close(panel);
        }
    }
    panel.addEventListener('ancore:task-modal-opened', () => {
        toggle.setAttribute('aria-expanded', 'true');
        const background = document.querySelectorAll('main.main-content, .sidebar, [data-app-topbar]');
        inertElements = Array.from(background).filter(element => !element.inert);
        inertElements.forEach(element => { element.inert = true; });
        controllers.get(panel).load();
    });
    panel.addEventListener('ancore:task-modal-closed', () => {
        closeActionMenus();
        controllers.get(panel)?.abort();
        toggle.setAttribute('aria-expanded', 'false');
        inertElements.forEach(element => { element.inert = false; });
        inertElements = [];
    });
    toggle.addEventListener('click', event => { event.preventDefault(); setOpen(!isOpen()); });
    window.addEventListener('ancore:global-search-open', () => setOpen(false));
    window.addEventListener('ancore:workspace-menu-open', () => setOpen(false));
    window.addEventListener('ancore:sidebar-toggle', () => setOpen(false));
    document.addEventListener('ancore:content-unloading', () => setOpen(false));
    document.addEventListener('ancore:content-loaded', () => { setOpen(false); init(); refreshSummary(); scheduleRefresh(); });
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshSummary(); scheduleRefresh(); });
    window.addEventListener('pageshow', event => { if (event.persisted) refreshSummary(); scheduleRefresh(); });
    window.addEventListener('online', refreshSummary);
    window.AncoreNotificationCenter = { refresh: refreshSummary };
    init();
    refreshSummary();
    scheduleRefresh();
})();
