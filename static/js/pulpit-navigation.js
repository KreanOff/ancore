(function () {
    if (window.ancorePulpitNavigationLoaded) return;
    window.ancorePulpitNavigationLoaded = true;
    let controller;
    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        document.addEventListener('submit', async event => {
            const form = event.target.closest('[data-sidebar-pulpit-favorite]');
            if (!form) return;
            event.preventDefault();
            const button = form.querySelector('button');
            if (button.disabled) return;
            const dashboardId = form.closest('[data-sidebar-pulpit-row]').dataset.sidebarPulpitRow;
            const url = window.location.href;
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            try {
                const response = await fetch(form.action, {
                    method: 'POST', body: new FormData(form), credentials: 'same-origin',
                    headers: { 'X-Pulpit-Navigation': 'true' },
                    signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]),
                });
                if (!response.ok || response.redirected || !(await response.json()).saved) throw new Error('Nie udało się zmienić oznaczenia gwiazdką. Spróbuj ponownie.');
                if (signal.aborted || window.location.href !== url) return;
                if (!await window.AncoreApp?.navigate(url, { replace: true })) window.location.reload();
                const focus = document.querySelector(`#sidebar-pulpits-subnav [data-sidebar-pulpit-row="${dashboardId}"] [data-row-actions-toggle]`)
                    || document.querySelector('[data-sidebar-group="pulpits"] [data-sidebar-group-toggle]');
                focus?.focus({ preventScroll: true });
            } catch (error) {
                if (!signal.aborted) window.showNotification?.(error.message, 'error');
            } finally {
                button.disabled = false;
                button.removeAttribute('aria-busy');
            }
        }, { signal });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
