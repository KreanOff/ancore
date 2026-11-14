(function () {
    const restoreForms = new Set();

    function initializeLoadingForms() {
        const overlay = document.querySelector('[data-auth-loading-overlay]');
        if (!overlay) return;
        document.querySelectorAll('form[data-auth-loading]').forEach((form) => {
            if (form.closest('[data-react-screen]') || form.dataset.loadingReady === 'true') return;
            form.dataset.loadingReady = 'true';
            const shell = form.closest('.auth-shell');
            const label = form.querySelector('.auth-submit-label');
            const originalLabel = label?.textContent;
            let pending = false;
            let wasInert = false;
            let buttons = [];
            const restore = () => {
                if (!pending) return;
                pending = false;
                form.removeAttribute('aria-busy');
                buttons.forEach((button) => { button.disabled = false; });
                if (shell) shell.inert = wasInert;
                if (label) label.textContent = originalLabel;
                overlay.dataset.loadingActive = 'false';
                overlay.setAttribute('aria-hidden', 'true');
                overlay.querySelector('[data-auth-loading-status]').textContent = '';
                restoreForms.delete(restore);
            };
            form.addEventListener('submit', (event) => {
                if (event.defaultPrevented) return;
                if (pending) {
                    event.preventDefault();
                    return;
                }
                pending = true;
                form.setAttribute('aria-busy', 'true');
                // Keep native field values enabled so the POST retains its complete payload.
                buttons = [...form.querySelectorAll('button:not(:disabled)')];
                buttons.forEach((button) => { button.disabled = true; });
                wasInert = Boolean(shell?.inert);
                if (shell) shell.inert = true;
                if (label) label.textContent = form.dataset.authLoading;
                overlay.querySelector('[data-auth-loading-status]').textContent = form.dataset.authLoading;
                overlay.dataset.loadingActive = 'true';
                overlay.setAttribute('aria-hidden', 'false');
                restoreForms.add(restore);
            });
        });
    }

    function initializePasswordToggles() {
        document.querySelectorAll('[data-password-toggle]').forEach((toggle) => {
            if (toggle.closest('[data-react-root]')) return;
            if (toggle.dataset.passwordToggleReady === 'true') return;

            const inputId = toggle.getAttribute('aria-controls');
            const input = inputId ? document.getElementById(inputId) : null;
            if (!input) return;

            toggle.dataset.passwordToggleReady = 'true';
            toggle.addEventListener('click', () => {
                const shouldShow = input.type === 'password';
                input.type = shouldShow ? 'text' : 'password';
                toggle.setAttribute('aria-pressed', String(shouldShow));
                toggle.setAttribute('aria-label', shouldShow ? 'Ukryj hasło' : 'Pokaż hasło');
                input.focus({ preventScroll: true });
            });
        });
    }

    function initialize() {
        initializePasswordToggles();
        initializeLoadingForms();
    }

    window.addEventListener('pageshow', (event) => {
        if (event.persisted) restoreForms.forEach((restore) => restore());
    });
    document.addEventListener('ancore:content-loaded', initialize);
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, { once: true });
    } else {
        initialize();
    }
})();
