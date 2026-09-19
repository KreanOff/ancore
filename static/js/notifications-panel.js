(function () {
    const panel = document.querySelector('[data-notifications-panel]');
    const toggle = document.querySelector('[data-notifications-toggle]');
    const closeButton = document.querySelector('[data-notifications-close]');
    const backdrop = document.querySelector('[data-notifications-backdrop]');
    const content = document.querySelector('[data-notifications-content]');
    const count = document.querySelector('[data-notifications-count]');
    const status = document.querySelector('[data-notifications-status]');
    const switcher = toggle?.closest('[data-sidebar-view-switcher]');
    const defaultView = switcher?.querySelector('[data-sidebar-default-view]');
    const notificationsUrl = panel?.dataset.notificationsUrl || toggle?.href || '';
    let requestController = null;
    let restoreFocusTo = null;

    if (!panel || !toggle || !content || !notificationsUrl) return;

    function iconNode(iconName) {
        const icon = document.createElement('i');
        icon.setAttribute('data-icon', iconName);
        icon.setAttribute('aria-hidden', 'true');
        return icon;
    }

    function renderIcons(scope) {
        window.AncoreIcons?.render(scope);
    }

    function stateElement(kind, icon, title, copy) {
        const state = document.createElement('div');
        state.className = `global-search-state notifications-panel__state notifications-panel__state--${kind}`;
        const visual = document.createElement('span');
        visual.className = 'global-search-state__icon';
        visual.setAttribute('aria-hidden', 'true');
        visual.appendChild(iconNode(icon));
        const heading = document.createElement('h3');
        heading.textContent = title;
        const description = document.createElement('p');
        description.textContent = copy;
        state.append(visual, heading, description);
        return state;
    }

    function renderLoading() {
        const loading = document.createElement('div');
        loading.className = 'global-search-loading notifications-panel__loading';
        loading.setAttribute('aria-hidden', 'true');
        for (let index = 0; index < 6; index += 1) {
            const row = document.createElement('span');
            row.className = 'global-search-loading__row';
            row.innerHTML = '<span></span><span></span>';
            loading.appendChild(row);
        }
        content.replaceChildren(loading);
        count.hidden = true;
        status.textContent = 'Pobieranie powiadomień…';
    }

    function renderError() {
        const errorState = stateElement(
            'error',
            'wifi-off',
            'Nie udało się pobrać powiadomień',
            'Sprawdź połączenie i spróbuj ponownie za chwilę.'
        );
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'global-search-state__retry';
        retry.textContent = 'Spróbuj ponownie';
        retry.addEventListener('click', loadNotifications);
        errorState.appendChild(retry);
        content.replaceChildren(errorState);
        count.hidden = true;
        status.textContent = 'Wystąpił błąd podczas pobierania powiadomień.';
        renderIcons(content);
    }

    async function loadNotifications() {
        requestController?.abort();
        requestController = new AbortController();
        const controller = requestController;
        renderLoading();

        try {
            const response = await fetch(notificationsUrl, {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(`Notifications failed with ${response.status}`);
            const payload = await response.json();
            if (controller !== requestController) return;
            content.innerHTML = payload.html;
            count.textContent = String(payload.count);
            count.hidden = payload.count === 0;
            status.textContent = `Liczba powiadomień: ${payload.count}.`;
            renderIcons(content);
        } catch (error) {
            if (error.name !== 'AbortError') renderError();
        }
    }

    function isOpen() {
        return toggle.getAttribute('aria-expanded') === 'true';
    }

    function syncSwitcher() {
        const items = Array.from(switcher?.querySelectorAll('.sidebar-view-switcher__item') || []);
        const expandedItem = items.find(item => item.getAttribute('aria-expanded') === 'true');

        items.forEach(function (item) {
            const isCurrentPage = item.getAttribute('aria-current') === 'page';
            item.classList.toggle('is-active', expandedItem ? item === expandedItem : isCurrentPage);
        });
    }

    function setOpen(open) {
        if (open === isOpen()) {
            if (open) closeButton?.focus({ preventScroll: true });
            return;
        }

        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        syncSwitcher();
        document.body.classList.toggle('notifications-panel-open', open);
        panel.hidden = !open;
        backdrop.hidden = !open;

        if (open) {
            restoreFocusTo = document.activeElement;
            window.dispatchEvent(new CustomEvent('ancore:notifications-open'));
            loadNotifications();
            window.setTimeout(function () {
                closeButton?.focus({ preventScroll: true });
            }, 20);
        } else {
            requestController?.abort();
            restoreFocusTo?.focus?.({ preventScroll: true });
            restoreFocusTo = null;
        }
    }

    toggle.addEventListener('click', function (event) {
        event.preventDefault();
        setOpen(!isOpen());
    });
    defaultView?.addEventListener('click', function (event) {
        if (!isOpen()) return;
        event.preventDefault();
        setOpen(false);
    });
    closeButton?.addEventListener('click', function () {
        setOpen(false);
    });
    backdrop?.addEventListener('click', function () {
        setOpen(false);
    });
    content.addEventListener('click', function (event) {
        if (event.target.closest('[data-notification-item]')) setOpen(false);
    });
    window.addEventListener('ancore:global-search-open', function () {
        setOpen(false);
    });

    document.addEventListener('keydown', function (event) {
        if (!isOpen()) return;
        if (event.key === 'Escape') {
            event.preventDefault();
            setOpen(false);
            return;
        }
        if (event.key !== 'Tab') return;
        const focusable = Array.from(panel.querySelectorAll('button:not([hidden]), a[href]'))
            .filter(element => !element.disabled && element.offsetParent !== null);
        if (!focusable.length) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });
})();
