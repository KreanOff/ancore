(function () {
    if (window.ancoreSpaceNavigationLoaded) return;
    window.ancoreSpaceNavigationLoaded = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        document.addEventListener('submit', async event => {
            const form = event.target.closest('[data-sidebar-space-favorite], [data-space-directory-favorite]');
            if (!form) return;
            event.preventDefault();
            const button = form.querySelector('button');
            if (button.disabled) return;
            const directoryRow = form.closest('[data-space-directory-row]');
            const spaceId = directoryRow?.dataset.spaceDirectoryRow || form.closest('[data-sidebar-space-row]').dataset.sidebarSpaceRow;
            const focusSelector = directoryRow
                ? `[data-space-directory-row="${spaceId}"] [data-row-actions-toggle]`
                : `#sidebar-spaces-subnav [data-sidebar-space-row="${spaceId}"] [data-row-actions-toggle]`;
            const url = window.location.href;
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            try {
                const response = await fetch(form.action, {
                    method: 'POST', body: new FormData(form), credentials: 'same-origin',
                    headers: { 'X-Space-Navigation': 'true' },
                    signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]),
                });
                if (!response.ok || response.redirected || !(await response.json()).saved) throw new Error('Nie udało się zmienić oznaczenia gwiazdką. Spróbuj ponownie.');
                if (signal.aborted || window.location.href !== url) return;
                if (!await window.AncoreApp?.navigate(url, { replace: true })) window.location.reload();
                const focusTarget = document.querySelector(focusSelector) || document.querySelector('.main-content h1');
                if (focusTarget?.matches('h1')) focusTarget.setAttribute('tabindex', '-1');
                focusTarget?.focus({ preventScroll: true });
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
