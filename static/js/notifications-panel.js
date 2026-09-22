(function () {
    if (window.AncoreNotificationCenter) return;
    const panel = document.querySelector('[data-notifications-panel]');
    const toggle = document.querySelector('[data-notifications-toggle]');
    const backdrop = document.querySelector('[data-notifications-backdrop]');
    if (!panel || !toggle) return;
    const controllers = new Map();
    let summaryRequest = null;
    let refreshTimer = null;
    let restoreFocus = null;
    let revision = null;
    let previousUnread = null;
    let inertElements = [];
    const isOpen = () => !panel.hidden;
    const icons = scope => window.AncoreIcons?.render(scope);

    function updateSummary(payload) {
        const unread = Number(payload.unread_count);
        const pending = Number(payload.pending_invitation_count);
        if (!Number.isInteger(unread) || !Number.isInteger(pending)) return;
        const label = `Nieprzeczytane: ${unread}. Oczekujące zaproszenia: ${pending}.`;
        const indicator = document.querySelector('[data-notifications-pending]');
        if (indicator) indicator.hidden = unread === 0 && pending === 0;
        document.querySelector('[data-notifications-invitation-status]').textContent = label;
        toggle.title = `Powiadomienia · ${label}`;
        document.querySelectorAll('[data-notifications-count], [data-notifications-unread-count]').forEach(node => {
            node.textContent = String(unread);
            if (node.matches('[data-notifications-count]')) node.hidden = unread === 0;
        });
        const nextRevision = JSON.stringify(payload.revision);
        if (revision !== null && (revision !== nextRevision || previousUnread !== unread)) {
            controllers.forEach((controller, root) => {
                if (!root.hidden && controller.loaded) root.querySelector('[data-notification-new-items]').hidden = false;
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
        let request = null;
        let mutating = false;
        let cursor = root.dataset.nextCursor || '';
        let snapshot = root.dataset.snapshot || '';
        let view = root.querySelector('[data-notification-filter][aria-pressed="true"]')?.dataset.notificationFilter || 'all';
        const controller = { loaded: Boolean(snapshot), load, abort: () => request?.abort() };

        function updateLocation() {
            if (root === panel) return;
            const url = new URL(location.href);
            url.searchParams.delete('cursor');
            if (view === 'all') url.searchParams.delete('view');
            else url.searchParams.set('view', view);
            const workspace = root.querySelector('[data-notification-workspace]').value;
            if (workspace) url.searchParams.set('workspace', workspace);
            else url.searchParams.delete('workspace');
            history.replaceState(history.state, '', url);
        }

        function reportError(message) {
            error.textContent = message;
            error.hidden = false;
            status.textContent = message;
        }

        async function load({ append = false, quiet = false, focusKey = '' } = {}) {
            request?.abort();
            request = new AbortController();
            const activeRequest = request;
            let timedOut = false;
            const timeout = setTimeout(() => { timedOut = true; activeRequest.abort(); }, 20000);
            error.hidden = true;
            content.setAttribute('aria-busy', 'true');
            readAll.disabled = true;
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
                readAll.disabled = payload.filtered_unread_count === 0;
                pagination.hidden = !cursor;
                root.querySelector('[data-notification-progress]').textContent = `${content.querySelectorAll('[data-notification-item]').length} z ${payload.total}`;
                root.querySelector('[data-notification-new-items]').hidden = true;
                status.textContent = `Powiadomienia: ${payload.total}. Nieprzeczytane: ${payload.filtered_unread_count}.`;
                icons(content);
                if (focusKey) {
                    const row = Array.from(content.querySelectorAll('[data-notification-item]')).find(item => item.dataset.notificationKey === focusKey);
                    (row?.querySelector('[data-notification-action]') || content).focus({ preventScroll: true });
                }
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

        async function mutate(action, key = '', link = null) {
            if (mutating) return;
            mutating = true;
            error.hidden = true;
            request?.abort();
            summaryRequest?.abort();
            summaryRequest = null;
            const buttons = root.querySelectorAll('[data-notification-action], [data-notification-read-all]');
            buttons.forEach(button => { button.disabled = true; });
            const mutationRequest = new AbortController();
            const timeout = setTimeout(() => mutationRequest.abort(), 15000);
            try {
                const body = new URLSearchParams({ action, key, snapshot });
                const response = await fetch(root.dataset.notificationsActionUrl, {
                    method: 'POST', credentials: 'same-origin', signal: mutationRequest.signal,
                    headers: { 'X-CSRFToken': root.querySelector('[name=csrfmiddlewaretoken]').value, 'X-Requested-With': 'XMLHttpRequest' }, body,
                });
                const payload = await response.json().catch(() => ({}));
                if (!response.ok) throw new Error(payload.error || 'Nie udało się zapisać zmiany. Spróbuj ponownie.');
                updateSummary(payload);
                if (link) {
                    setOpen(false);
                    window.location.assign(link.href);
                } else {
                    await load({ quiet: true, focusKey: key });
                    status.textContent = action === 'archive' ? 'Powiadomienie przeniesione do archiwum.' : action === 'restore' ? 'Powiadomienie przywrócone.' : 'Stan powiadomień zapisany.';
                }
            } catch (failure) {
                reportError(failure.name === 'AbortError' || failure instanceof TypeError ? 'Brak połączenia. Zmiana nie została potwierdzona — spróbuj ponownie.' : failure.message);
                buttons.forEach(button => { if (button.isConnected) button.disabled = false; });
            } finally {
                clearTimeout(timeout);
                mutating = false;
            }
        }

        root.addEventListener('click', event => {
            const filter = event.target.closest('[data-notification-filter]');
            if (filter) {
                view = filter.dataset.notificationFilter;
                root.querySelectorAll('[data-notification-filter]').forEach(button => button.setAttribute('aria-pressed', String(button === filter)));
                updateLocation();
                load();
            } else if (event.target.closest('[data-notification-refresh], [data-notification-new-items]')) load();
            else if (event.target.closest('[data-notification-more]')) load({ append: true });
            else if (event.target.closest('[data-notification-read-all]')) mutate('read_all');
            else if (event.target.closest('[data-notification-action]')) {
                const button = event.target.closest('[data-notification-action]');
                mutate(button.dataset.notificationAction, button.closest('[data-notification-item]').dataset.notificationKey);
            } else {
                const link = event.target.closest('[data-notification-open]');
                if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
                    event.preventDefault();
                    mutate('read', link.closest('[data-notification-item]').dataset.notificationKey, link);
                }
            }
        });
        root.querySelector('[data-notification-workspace]').addEventListener('change', () => { updateLocation(); load(); });
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
        toggle.setAttribute('aria-expanded', String(open));
        document.body.classList.toggle('notifications-panel-open', open);
        panel.hidden = !open;
        backdrop.hidden = !open;
        const items = toggle.closest('[data-sidebar-view-switcher]')?.querySelectorAll('.sidebar-view-switcher__item') || [];
        items.forEach(item => item.classList.toggle('is-active', open ? item === toggle : item.getAttribute('aria-current') === 'page'));
        if (open) {
            restoreFocus = document.activeElement;
            window.dispatchEvent(new CustomEvent('ancore:notifications-open'));
            inertElements = Array.from(document.querySelectorAll('main.main-content, .sidebar')).filter(element => !element.inert);
            inertElements.forEach(element => { element.inert = true; });
            controllers.get(panel).load();
            panel.querySelector('[data-notifications-close]').focus({ preventScroll: true });
        } else {
            controllers.get(panel)?.abort();
            inertElements.forEach(element => { element.inert = false; });
            inertElements = [];
            restoreFocus?.focus?.({ preventScroll: true });
            restoreFocus = null;
        }
    }
    toggle.addEventListener('click', event => { event.preventDefault(); setOpen(!isOpen()); });
    panel.querySelector('[data-notifications-close]').addEventListener('click', () => setOpen(false));
    backdrop.addEventListener('click', () => setOpen(false));
    window.addEventListener('ancore:global-search-open', () => setOpen(false));
    document.addEventListener('keydown', event => {
        if (!isOpen()) return;
        if (event.key === 'Escape') { event.preventDefault(); setOpen(false); }
        if (event.key !== 'Tab') return;
        const elements = Array.from(panel.querySelectorAll('button:not(:disabled), a[href], select:not(:disabled), input:not([type="hidden"]):not(:disabled), [tabindex="0"]'))
            .filter(element => element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden');
        const first = elements[0], last = elements[elements.length - 1];
        if (event.shiftKey && (document.activeElement === first || !panel.contains(document.activeElement))) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) { event.preventDefault(); first?.focus(); }
    });
    document.addEventListener('ancore:content-loaded', () => { setOpen(false); init(); refreshSummary(); scheduleRefresh(); });
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshSummary(); scheduleRefresh(); });
    window.addEventListener('pageshow', event => { if (event.persisted) refreshSummary(); scheduleRefresh(); });
    window.addEventListener('online', refreshSummary);
    window.AncoreNotificationCenter = { refresh: refreshSummary };
    init();
    refreshSummary();
    scheduleRefresh();
})();
