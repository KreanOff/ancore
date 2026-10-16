(function () {
    const version = '20261016-global-panels';
    if (window.AncoreTaskModals?.version === version) return;
    window.AncoreTaskModals?.dispose?.();
    const controller = new AbortController();
    const modalReturnFocus = new WeakMap();
    const modalCloseTokens = new WeakMap();

    function openModal(modal, focusTarget, onOpen) {
        if (!modal) return;
        modalCloseTokens.delete(modal);
        if (!modal.classList.contains('is-open') && !modalReturnFocus.has(modal)) {
            const activeElement = document.activeElement;
            const rowActionToggle = activeElement?.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]');
            modalReturnFocus.set(modal, rowActionToggle || activeElement);
        }
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
        if (onOpen) onOpen();
        window.AncoreCustomSelect?.refresh(modal);
        modal.dispatchEvent(new CustomEvent('ancore:task-modal-opened', { bubbles: true }));
        setTimeout(() => {
            if (modal.classList.contains('is-open') && !modal.inert && !modal.contains(document.activeElement)) {
                focusTarget?.focus();
            }
        }, 50);
    }

    function closeModal(modal) {
        if (!modal || !modal.classList.contains('is-open')) return;
        if (!modal.dispatchEvent(new CustomEvent('ancore:task-modal-before-close', { bubbles: true, cancelable: true }))) return;
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        if (!document.querySelector('.tasks-modal.is-open')) {
            document.body.classList.remove('modal-open');
        }
        const token = {};
        modalCloseTokens.set(modal, token);
        const finish = () => {
            if (modalCloseTokens.get(modal) !== token) return;
            modalCloseTokens.delete(modal);
            modal.dispatchEvent(new CustomEvent('ancore:task-modal-closed', { bubbles: true }));
            const returnFocus = modalReturnFocus.get(modal);
            if (returnFocus instanceof HTMLElement && returnFocus.isConnected) {
                returnFocus.focus({ preventScroll: true });
            }
            modalReturnFocus.delete(modal);
        };
        const dialog = modal.querySelector(':scope > .tasks-modal__dialog');
        const animations = modal.classList.contains('app-modal-panel--compact') ? dialog?.getAnimations() || [] : [];
        if (animations.length) Promise.all(animations.map(animation => animation.finished.catch(() => {}))).then(finish);
        else finish();
    }

    window.AncoreTaskModals = { version, open: openModal, close: closeModal, dispose: () => controller.abort() };

    document.addEventListener('keydown', event => {
        if (!document.querySelector('[data-react-root="page"], [data-react-global-panels]') || document.querySelector('.confirm-modal-overlay')) return;
        if (document.querySelector('[data-profile-photo-modal]:not([hidden])')) return;
        const modal = [...document.querySelectorAll('.tasks-modal.is-open')].at(-1);
        if (!modal) return;
        if (event.key === 'Escape') {
            if (event.target.matches('input[role=combobox][aria-expanded=true], input[role=combobox][aria-busy=true]')) return;
            if (document.querySelector('.ancore-dropdown-layer:popover-open')) return;
            const select = modal.querySelector('.ancore-custom-select.is-open .ancore-custom-select__button');
            if (select) { window.AncoreCustomSelect?.closeAll(); select.focus(); }
            else closeModal(modal);
            event.preventDefault(); event.stopImmediatePropagation();
        } else if (event.key === 'Tab') {
            const controls = [...modal.querySelectorAll('button, a[href], input, select, textarea, [tabindex]')].filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length && !element.closest('[inert]'));
            const first = controls[0], last = controls.at(-1);
            if (first && (event.shiftKey ? document.activeElement === first : document.activeElement === last)) { event.preventDefault(); (event.shiftKey ? last : first).focus(); }
        }
    }, { capture: true, signal: controller.signal });
    document.addEventListener('click', event => {
        if (!document.querySelector('[data-react-root="page"], [data-react-global-panels]')) return;
        const button = event.target.closest('[data-close-modal]');
        if (button) { event.preventDefault(); closeModal(button.closest('.tasks-modal')); }
    }, { signal: controller.signal });
})();
