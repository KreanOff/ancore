(function () {
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializePasswordToggles, { once: true });
    } else {
        initializePasswordToggles();
    }
})();
