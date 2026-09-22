(function () {
    'use strict';
    let cleanup = () => {};
    function init() {
        cleanup();
        cleanup = () => {};
        const page = document.querySelector('[data-workplace-team], [data-team-modal-page]');
        if (!page) return;
        const controller = new AbortController();
        const options = { signal: controller.signal };
        const modals = [...document.querySelectorAll('[data-team-modal]')];
        const states = new Map();
        function restore(state) {
            state.inertElements.forEach(element => { element.inert = false; });
            state.inertElements = [];
        }
        function syncModal(modal) {
            const state = states.get(modal);
            const open = modal.classList.contains('is-open');
            page.querySelectorAll(`[data-team-modal-open="${modal.id}"]`).forEach(trigger => trigger.setAttribute('aria-expanded', String(open)));
            if (open === state.wasOpen) return;
            state.wasOpen = open;
            if (open) {
                state.previousFocus = document.activeElement;
                document.body.classList.add('modal-open');
                modal.setAttribute('aria-hidden', 'false');
                for (let node = modal; node && node !== document.body; node = node.parentElement) {
                    [...node.parentElement.children].forEach(sibling => {
                        if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert && !sibling.matches('#app-notifications')) {
                            sibling.inert = true;
                            state.inertElements.push(sibling);
                        }
                    });
                }
                window.AncoreCustomSelect?.refresh(modal);
                const focusTarget = modal.querySelector('[aria-invalid="true"]')
                    || modal.querySelector('input[type="email"]')
                    || modal.querySelector('[data-ancore-custom-select-toggle]')
                    || modal.querySelector('[data-close-modal]');
                focusTarget?.focus();
            } else {
                restore(state);
                if (modal.matches('[data-invitation-response-modal]')) {
                    const url = new URL(window.location.href);
                    url.searchParams.delete('invitation');
                    window.history.replaceState(window.history.state, '', url);
                }
                const target = state.previousFocus instanceof HTMLElement && state.previousFocus !== document.body
                    && !modal.contains(state.previousFocus) && state.previousFocus.offsetParent !== null
                    ? state.previousFocus : page.querySelector(`[data-team-modal-open="${modal.id}"]`);
                if (target?.isConnected) target.focus({ preventScroll: true });
            }
        }
        // tasks.js owns shared close buttons, Escape, backdrop and focus trap.
        const observers = modals.map(modal => {
            states.set(modal, { wasOpen: false, inertElements: [], previousFocus: null });
            const observer = new MutationObserver(() => syncModal(modal));
            observer.observe(modal, { attributes: true, attributeFilter: ['class'] });
            syncModal(modal);
            return observer;
        });
        page.addEventListener('click', event => {
            const trigger = event.target.closest('[data-team-modal-open]');
            if (!trigger) return;
            const modal = document.getElementById(trigger.dataset.teamModalOpen);
            if (!states.has(modal)) return;
            if (trigger.dataset.teamRoleUrl) {
                const form = modal.querySelector('[data-team-role-form]');
                form.action = trigger.dataset.teamRoleUrl;
                form.elements.role.value = trigger.dataset.teamRole;
                modal.querySelector('[data-team-role-person]').textContent = trigger.dataset.teamPerson;
            }
            modal.classList.add('is-open');
            syncModal(modal);
        }, options);
        document.querySelectorAll('[data-team-invite-form], [data-team-role-form], [data-team-response-form]').forEach(form => {
            form.addEventListener('submit', event => {
                if (form.dataset.submitting) { event.preventDefault(); return; }
                form.dataset.submitting = 'true';
                if (form.matches('[data-team-response-form]')) {
                    const action = document.createElement('input');
                    action.type = 'hidden';
                    action.name = 'action';
                    action.value = event.submitter?.value || '';
                    form.appendChild(action);
                    form.querySelectorAll('[type="submit"]').forEach(button => { button.disabled = true; });
                    if (event.submitter) event.submitter.textContent = 'Zapisywanie…';
                    return;
                }
                const button = form.querySelector('[type="submit"]');
                button.disabled = true;
                button.textContent = 'Zapisywanie…';
            }, options);
        });
        page.addEventListener('submit', event => {
            const form = event.target.closest('[data-team-remove]');
            if (!form || form.dataset.confirmed) return;
            event.preventDefault();
            window.showConfirmModal({
                title: 'Odebrać dostęp do Workspace?',
                message: 'Dane zespołu pozostaną bez zmian. Otwarte edytory Office zostaną zamknięte — pozostali członkowie muszą ponownie otworzyć pliki.',
                confirmText: 'Odbierz dostęp',
                onConfirm: () => { form.dataset.confirmed = 'true'; form.requestSubmit(); }
            });
        }, options);
        cleanup = () => { controller.abort(); observers.forEach(observer => observer.disconnect()); states.forEach(restore); };
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
