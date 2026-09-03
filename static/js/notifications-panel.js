(function () {
    const panel = document.querySelector('[data-notifications-panel]');
    const toggle = document.querySelector('[data-notifications-toggle]');
    const closeButton = document.querySelector('[data-notifications-close]');
    const backdrop = document.querySelector('[data-notifications-backdrop]');
    const content = document.querySelector('[data-notifications-content]');
    const count = document.querySelector('[data-notifications-count]');
    const status = document.querySelector('[data-notifications-status]');
    const defaultView = document.querySelector('[data-sidebar-view-switcher] .sidebar-view-switcher__item:first-child');
    const notificationsUrl = panel?.dataset.notificationsUrl || toggle?.href || '';
    const toggleWasCurrent = toggle?.getAttribute('aria-current') === 'page';
    const defaultViewWasCurrent = defaultView?.getAttribute('aria-current') === 'page';
    let requestController = null;
    let restoreFocusTo = null;

    if (!panel || !toggle || !content || !notificationsUrl) return;

    function iconNode(iconName) {
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', iconName);
        icon.setAttribute('aria-hidden', 'true');
        return icon;
    }

    function renderIcons(scope) {
        if (window.renderLucideIcons) {
            window.renderLucideIcons(scope);
        } else if (window.lucide?.createIcons) {
            window.lucide.createIcons({ attrs: { 'aria-hidden': 'true' } });
        }
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

    function updateSwitcher(open) {
        toggle.classList.toggle('is-active', open || toggleWasCurrent);
        defaultView?.classList.toggle('is-active', !open && defaultViewWasCurrent);
    }

    function setOpen(open) {
        if (open === isOpen()) {
            if (open) closeButton?.focus({ preventScroll: true });
            return;
        }

        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        updateSwitcher(open);
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
