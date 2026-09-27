(function () {
    'use strict';
    if (window.ancoreWorkplaceTeam) return;
    window.ancoreWorkplaceTeam = true;
    let cleanup = () => {};
    function initInvitationPicker(picker, options) {
        const input = picker.querySelector('[data-team-invite-search]');
        const menu = picker.querySelector('[role="listbox"]');
        const status = picker.querySelector('[role="status"]');
        const selected = picker.querySelector('[data-team-invite-selected]');
        let timer, request, version = 0, activeIndex = -1, people = [], selectedEmail = '';
        function cancelRequest() {
            clearTimeout(timer);
            request?.abort();
            version += 1;
        }
        function close() {
            cancelRequest();
            menu.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
            activeIndex = -1;
            if (status.dataset.loading) {
                status.textContent = '';
                delete status.dataset.loading;
            }
        }
        function choose(person) {
            close();
            input.value = person.email;
            selectedEmail = person.email;
            selected.innerHTML = person.html;
            window.AncoreIcons?.render(selected);
            selected.hidden = false;
            status.textContent = `${picker.dataset.selectedLabel || 'Zapraszasz'}: ${person.name}.`;
            input.focus({ preventScroll: true });
        }
        function search() {
            close();
            selectedEmail = '';
            selected.hidden = true;
            selected.replaceChildren();
            people = [];
            menu.replaceChildren();
            const query = input.value.trim();
            if (query.length < 2) {
                status.textContent = 'Wpisz co najmniej 2 znaki, aby wyszukać osobę.';
                return;
            }
            const currentVersion = version;
            status.textContent = 'Szukam osób…';
            status.dataset.loading = 'true';
            timer = setTimeout(async () => {
                request = new AbortController();
                const url = new URL(picker.dataset.candidatesUrl, window.location.href);
                url.searchParams.set('q', query);
                try {
                    const response = await fetch(url, {
                        signal: request.signal, headers: { 'X-Requested-With': 'XMLHttpRequest' }
                    });
                    if (!response.ok) throw new Error('Lookup failed');
                    const data = await response.json();
                    if (currentVersion !== version || !picker.isConnected) return;
                    delete status.dataset.loading;
                    people = data.results;
                    const exact = people.find(person => person.email.toLocaleLowerCase() === query.toLocaleLowerCase());
                    if (exact) { choose(exact); return; }
                    people.forEach((person, index) => {
                        const button = document.createElement('button');
                        button.type = 'button';
                        button.className = 'tasks-project-menu-button';
                        button.id = `team-invite-person-${index}`;
                        button.dataset.personIndex = String(index);
                        button.setAttribute('role', 'option');
                        button.setAttribute('aria-selected', 'false');
                        button.tabIndex = -1;
                        button.innerHTML = person.html;
                        menu.appendChild(button);
                    });
                    window.AncoreIcons?.render(menu);
                    menu.hidden = people.length === 0;
                    input.setAttribute('aria-expanded', String(people.length > 0));
                    status.textContent = !people.length
                        ? picker.hasAttribute('data-sharing-picker')
                            ? 'Nie znaleziono osoby, której można udostępnić. Sprawdź dane; obecni członkowie nie pojawiają się na liście.'
                            : 'Nie znaleziono osoby, którą można zaprosić. Sprawdź dane; członkowie i osoby z oczekującym zaproszeniem nie pojawiają się na liście.'
                        : data.has_more ? 'Pokazano 10 osób. Doprecyzuj wyszukiwanie lub wybierz osobę.'
                            : 'Wybierz osobę z listy.';
                } catch (error) {
                    if (error.name === 'AbortError' || currentVersion !== version) return;
                    delete status.dataset.loading;
                    status.textContent = 'Nie udało się pobrać podpowiedzi. Wpisz adres e-mail lub zmień tekst, aby spróbować ponownie.';
                }
            }, 250);
        }
        input.addEventListener('input', search, options);
        input.addEventListener('focus', () => {
            if (input.value.trim() && input.value.trim() !== selectedEmail) search();
        }, options);
        input.addEventListener('blur', cancelRequest, options);
        // Collapse after the click: hiding this inline list on blur would move
        // the modal's Cancel/Submit buttons between pointer down and pointer up.
        document.addEventListener('click', event => {
            if (event.target.closest('[data-team-modal-open]')?.dataset.teamModalOpen === picker.closest('.tasks-modal').id) return;
            if (!picker.contains(event.target)) close();
        }, options);
        // Keep focus on the combobox while selecting a result with a pointer.
        menu.addEventListener('mousedown', event => event.preventDefault(), options);
        menu.addEventListener('click', event => {
            const button = event.target.closest('[data-person-index]');
            if (button) choose(people[Number(button.dataset.personIndex)]);
        }, options);
        input.addEventListener('keydown', event => {
            if (event.isComposing) return;
            if (event.key === 'Tab') {
                close();
            } else if (event.key === 'Escape' && (!menu.hidden || status.dataset.loading)) {
                event.preventDefault();
                event.stopPropagation();
                close();
            } else if (!menu.hidden && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
                event.preventDefault();
                event.stopPropagation();
                if (event.key === 'Enter') { choose(people[Math.max(0, activeIndex)]); return; }
                activeIndex = activeIndex < 0 ? (event.key === 'ArrowDown' ? 0 : people.length - 1)
                    : (activeIndex + (event.key === 'ArrowDown' ? 1 : -1) + people.length) % people.length;
                [...menu.children].forEach((button, index) => button.setAttribute('aria-selected', String(index === activeIndex)));
                const active = menu.children[activeIndex];
                input.setAttribute('aria-activedescendant', active.id);
                active.scrollIntoView({ block: 'nearest' });
            }
        }, options);
        return close;
    }
    window.AncoreTeamInvitationPicker = { init: initInvitationPicker };
    function init() {
        cleanup();
        cleanup = () => {};
        const page = document.querySelector('[data-workplace-team], [data-team-modal-page]');
        if (!page) return;
        const controller = new AbortController();
        const options = { signal: controller.signal };
        const closePickers = [...document.querySelectorAll('[data-team-invite-picker]')]
            .map(picker => initInvitationPicker(picker, options));
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
                    || modal.querySelector('[data-team-invite-search], input[type="email"]')
                    || modal.querySelector('[data-ancore-custom-select-toggle]')
                    || modal.querySelector('[data-close-modal]');
                if (!modal.closest('[inert]')) focusTarget?.focus();
            } else {
                if (modal.querySelector('[data-team-invite-picker]')) closePickers.forEach(close => close());
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
                        || page.querySelector(`[data-workplace-row-modal="${modal.id}"] [data-row-actions-toggle]`)
                        || [...page.querySelectorAll(`[data-workplace-edit-open="${modal.id}"]`)]
                            .find(trigger => trigger.getClientRects().length)
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
        function openWorkplaceRow(row) {
            const link = row.querySelector('.workplaces-management__select[data-workplace-edit-open]');
            if (!link) return;
            link.focus({ preventScroll: true });
            link.click();
        }
        page.addEventListener('click', event => {
            const row = event.target.closest('[data-workplace-row-modal]');
            if (row && !event.defaultPrevented && event.button === 0
                && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey
                && !event.target.closest('a, button, input, select, textarea, label, form, [contenteditable], [data-row-actions], [data-column="select"], [data-column="action"]')
                && !window.getSelection()?.toString()) {
                openWorkplaceRow(row);
                return;
            }
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
            if (event.target.matches('[data-workplace-row-modal]')
                && ['Enter', ' '].includes(event.key) && !event.defaultPrevented
                && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
                event.preventDefault();
                openWorkplaceRow(event.target);
                return;
            }
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
        cleanup = () => { closePickers.forEach(close => close()); controller.abort(); observers.forEach(observer => observer.disconnect()); restoreBackground(); };
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
