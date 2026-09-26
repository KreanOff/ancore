(function () {
    'use strict';
    if (window.ancoreWorkplaceTeam) return;
    window.ancoreWorkplaceTeam = true;
    let cleanup = () => {};
    function init() {
        cleanup();
        cleanup = () => {};
        const page = document.querySelector('[data-workplace-team], [data-team-modal-page]');
        if (!page) return;
        const controller = new AbortController();
        const options = { signal: controller.signal };
        page.querySelectorAll('[data-team-selection]').forEach(table => {
            const selectAll = table.querySelector('[data-team-select-all]');
            const inputs = [...table.querySelectorAll('[data-team-select]')];
            function syncSelection() {
                const selected = inputs.filter(input => input.checked).length;
                inputs.forEach(input => {
                    input.closest('.tasks-directory-row').classList.toggle('checked', input.checked);
                });
                selectAll.checked = inputs.length > 0 && selected === inputs.length;
                selectAll.indeterminate = selected > 0 && selected < inputs.length;
                selectAll.disabled = inputs.length === 0;
            }
            table.addEventListener('change', event => {
                if (event.target === selectAll) {
                    inputs.forEach(input => { input.checked = selectAll.checked; });
                } else if (!event.target.matches('[data-team-select]')) return;
                syncSelection();
            }, options);
            // The whole selection column is clickable, as in project tables.
            table.addEventListener('click', event => {
                if (event.defaultPrevented || event.target.closest('a, input, button, select, textarea')) return;
                const header = event.target.closest('.tasks-directory-header [data-column="select"]');
                const row = event.target.closest('.tasks-directory-row');
                const input = header ? selectAll : row?.querySelector('[data-team-select]');
                if (!input || input.disabled) return;
                if (!header && (event.clientX < row.getBoundingClientRect().left
                    || event.clientX >= input.nextElementSibling.getBoundingClientRect().left)) return;
                input.focus({ preventScroll: true });
                input.click();
            }, options);
            syncSelection();
        });
        const modals = [...document.querySelectorAll('[data-team-modal], [data-workplace-edit-modal]')];
        const states = new Map();
        let inertElements = [];
        function restoreBackground() {
            inertElements.forEach(element => { element.inert = false; });
            inertElements = [];
        }
        function syncBackground() {
            restoreBackground();
            const top = modals.filter(modal => modal.classList.contains('is-open')).at(-1);
            for (let node = top; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert && !sibling.matches('#app-notifications')) {
                        sibling.inert = true;
                        inertElements.push(sibling);
                    }
                });
            }
        }
        function selectTab(modal, name, focus = false) {
            const tabs = [...modal.querySelectorAll('[data-workplace-tab]')];
            const selected = tabs.find(tab => tab.dataset.workplaceTab === name);
            if (!selected) return;
            tabs.forEach(tab => {
                tab.setAttribute('aria-selected', String(tab === selected));
                tab.tabIndex = tab === selected ? 0 : -1;
            });
            modal.querySelectorAll('[data-workplace-tab-panel]').forEach(panel => {
                panel.hidden = panel.dataset.workplaceTabPanel !== name;
            });
            modal.querySelectorAll('[data-workplace-main-action]').forEach(button => { button.hidden = name !== 'main'; });
            if (focus) selected.focus();
        }
        function syncModal(modal) {
            const state = states.get(modal);
            const open = modal.classList.contains('is-open');
            page.querySelectorAll(`[data-team-modal-open="${modal.id}"]`).forEach(trigger => trigger.setAttribute('aria-expanded', String(open)));
            page.querySelectorAll(`[data-workplace-edit-open="${modal.id}"]`).forEach(trigger => trigger.setAttribute('aria-expanded', String(open)));
            if (open === state.wasOpen) return;
            state.wasOpen = open;
            syncBackground();
            if (open) {
                state.previousFocus = document.activeElement?.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || document.activeElement;
                document.body.classList.add('modal-open');
                modal.setAttribute('aria-hidden', 'false');
                window.AncoreCustomSelect?.refresh(modal);
                const focusTarget = modal.querySelector('[aria-invalid="true"]')
                    || modal.querySelector('[data-workplace-tab][aria-selected="true"]')
                    || modal.querySelector('input[type="email"]')
                    || modal.querySelector('[data-ancore-custom-select-toggle]')
                    || modal.querySelector('[data-close-modal]');
                if (!modal.closest('[inert]')) focusTarget?.focus();
            } else {
                if (modal.matches('[data-invitation-response-modal]')) {
                    const url = new URL(window.location.href);
                    url.searchParams.delete('invitation');
                    window.history.replaceState(window.history.state, '', url);
                }
                if (modal.matches('[data-workplace-edit-modal]')) {
                    const url = new URL(modal.dataset.workplaceReturnUrl, window.location.href);
                    window.history.replaceState(window.history.state, '', url);
                }
                const target = state.previousFocus instanceof HTMLElement && state.previousFocus !== document.body
                    && !modal.contains(state.previousFocus) && state.previousFocus.offsetParent !== null
                    ? state.previousFocus : ([...page.querySelectorAll(`[data-team-modal-open="${modal.id}"]`)]
                        .find(trigger => trigger.getClientRects().length)
                        || page.querySelector(`[data-workplace-edit-open="${modal.id}"]`)
                        || page.querySelector('[data-team-invitation-return]'));
                if (target?.isConnected) target.focus({ preventScroll: true });
            }
        }
        // tasks.js owns shared close buttons, Escape, backdrop and focus trap.
        const observers = modals.map(modal => {
            states.set(modal, { wasOpen: false, previousFocus: null });
            selectTab(modal, modal.dataset.initialTab || 'main');
            const observer = new MutationObserver(() => syncModal(modal));
            observer.observe(modal, { attributes: true, attributeFilter: ['class'] });
            syncModal(modal);
            return observer;
        });
        page.addEventListener('click', event => {
            const tab = event.target.closest('[data-workplace-tab]');
            if (tab) {
                selectTab(tab.closest('[data-workplace-edit-modal]'), tab.dataset.workplaceTab);
                return;
            }
            const editTrigger = event.target.closest('[data-workplace-edit-open]');
            if (editTrigger) {
                const modal = document.getElementById(editTrigger.dataset.workplaceEditOpen);
                if (!states.has(modal) || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                selectTab(modal, editTrigger.dataset.workplaceEditTab || 'main');
                window.AncoreTaskModals.open(modal);
                syncModal(modal);
                return;
            }
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
        page.addEventListener('keydown', event => {
            const tab = event.target.closest('[data-workplace-tab]');
            if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const modal = tab.closest('[data-workplace-edit-modal]');
            const tabs = [...modal.querySelectorAll('[data-workplace-tab]')];
            const index = tabs.indexOf(tab);
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
                : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
            selectTab(modal, tabs[next].dataset.workplaceTab, true);
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
        cleanup = () => { controller.abort(); observers.forEach(observer => observer.disconnect()); restoreBackground(); };
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
