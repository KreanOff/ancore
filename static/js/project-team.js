(function () {
    if (window.ancoreProjectTeam) return;
    window.ancoreProjectTeam = true;
    let cleanup = () => {};
    function initTeam(kind) {
        const isTask = kind === 'task';
        const form = document.getElementById(isTask ? 'task-detail-form' : `${kind}-rename-form`);
        const host = document.querySelector(`[data-project-team-modal-host="${kind}"]`);
        if (!form || !host) return () => {};
        const isKanban = form.dataset.teamApp === 'kanban';
        const controller = new AbortController();
        const options = { signal: controller.signal };
        const main = form.closest('.tasks-modal');
        const errorBox = form.querySelector('[data-project-team-error]');
        let url, version = 0, pending = false, tab = 'main', pickerController, closePickers = [], requestController;
        let previousFocus, inertElements = [];
        function restoreBackground() {
            inertElements.forEach(node => { node.inert = false; });
            inertElements = [];
        }
        function protectBackground(modal) {
            restoreBackground();
            for (let node = modal; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert && sibling.id !== 'app-notifications') {
                        sibling.inert = true; inertElements.push(sibling);
                    }
                });
            }
        }
        function selectTab(name, focus = false) {
            if (isTask) {
                const button = form.querySelector(`[data-task-tab="${name}"]`);
                button?.click();
                if (focus) button?.focus();
                return;
            }
            const tabs = [...form.querySelectorAll('[data-project-access-tab]')].filter(node => !node.hidden);
            if (!tabs.some(node => node.dataset.projectAccessTab === name)) name = 'main';
            tab = name;
            tabs.forEach(node => {
                const selected = node.dataset.projectAccessTab === name;
                node.setAttribute('aria-selected', String(selected)); node.tabIndex = selected ? 0 : -1;
                if (selected && focus) node.focus();
            });
            form.querySelectorAll('[data-project-access-panel]').forEach(node => { node.hidden = node.dataset.projectAccessPanel !== name; });
            form.querySelector(`#${kind}-rename-submit`).hidden = name !== 'main' || form.dataset.projectReadonly === 'true';
            form.querySelector('footer [data-close-modal]').textContent = name === 'main' && form.dataset.projectReadonly !== 'true' ? 'Anuluj' : 'Zamknij';
        }
        function clearPickers() {
            closePickers.forEach(close => close()); closePickers = [];
            pickerController?.abort();
        }
        function display(data) {
            clearPickers();
            form.querySelector('[data-project-team-members]').innerHTML = data.members;
            host.innerHTML = data.modals;
            host.querySelectorAll('form').forEach(node => { node.action = url; });
            window.AncoreIcons?.render(form); window.AncoreIcons?.render(host);
            window.AncoreCustomSelect?.refresh(host);
            document.dispatchEvent(new CustomEvent('ancore:modals-loaded', { detail: { root: host } }));
            pickerController = new AbortController();
            closePickers = [...host.querySelectorAll('[data-team-invite-picker]')].map(picker =>
                window.AncoreTeamInvitationPicker.init(picker, { signal: pickerController.signal }));
            if (!isTask) selectTab(tab);
        }
        async function request(body) {
            requestController?.abort(); requestController = new AbortController();
            const timer = setTimeout(() => requestController.abort(), 15000);
            try {
                const response = await fetch(url, { method: body ? 'POST' : 'GET', body,
                    signal: requestController.signal, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                if (response.redirected) throw new Error('Session expired');
                const data = await response.json();
                if (!response.ok) {
                    const messages = Object.values(data.errors || {}).flat().map(error => error.message);
                    throw new Error(messages.join(' ') || data.error || 'Nie udało się zapisać zmian. Zamknij i ponownie otwórz okno.');
                }
                return data;
            } finally { clearTimeout(timer); }
        }
        async function load(teamUrl) {
            const current = ++version;
            requestController?.abort(); clearPickers();
            url = teamUrl; if (!isTask) selectTab('main'); errorBox.hidden = true;
            form.querySelector('[data-project-team-members]').textContent = 'Ładowanie członków…';
            host.replaceChildren();
            if (!url) return;
            try { const data = await request(); if (current === version) display(data); }
            catch (error) { if (current === version && !controller.signal.aborted) { errorBox.textContent = 'Nie udało się pobrać członków. Zamknij i ponownie otwórz okno.'; errorBox.hidden = false; } }
        }
        function openChild(id, trigger) {
            const modal = host.querySelector('#' + id); if (!modal) return;
            previousFocus = trigger.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || trigger;
            const errors = modal.querySelector('[data-project-team-errors]'); errors.hidden = true;
            protectBackground(modal);
            window.AncoreTaskModals.open(modal, modal.querySelector('[data-team-invite-search], select'));
        }
        async function mutate(body, childForm) {
            if (pending) return;
            pending = true; errorBox.hidden = true;
            const errors = childForm?.querySelector('[data-project-team-errors]') || errorBox;
            errors.hidden = true;
            const controls = [...(childForm || form).querySelectorAll('button')].map(node => [node, node.disabled]);
            controls.forEach(([node]) => { node.disabled = true; });
            body.set('csrfmiddlewaretoken', form.elements.csrfmiddlewaretoken.value);
            try {
                const data = await request(body);
                pending = false;
                const child = childForm?.closest('.tasks-modal');
                if (child) window.AncoreTaskModals.close(child);
                if (body.get('action') === 'share') tab = 'members';
                display(data);
                if (isTask) selectTab('members', true);
                else form.querySelector(`[data-project-access-tab="${tab}"]`)?.focus();
                window.showNotification?.('Zmiany zapisane.', 'success');
            } catch (error) {
                if (!controller.signal.aborted) { errors.textContent = error.message; errors.hidden = false; }
            } finally { pending = false; controls.forEach(([node, disabled]) => { node.disabled = disabled; }); }
        }
        document.addEventListener(`ancore:${kind}-team-selected`, event => { if (event.target === form) load(event.detail.url); }, options);
        form.addEventListener('click', event => {
            const trigger = event.target.closest('button'); if (!trigger || pending) return;
            if (trigger.dataset.projectAccessTab) selectTab(trigger.dataset.projectAccessTab);
            if (trigger.hasAttribute('data-project-share-open')) {
                host.querySelector('[name="email"]').value = '';
                host.querySelector('[data-team-invite-selected]').hidden = true;
                openChild(`${kind}-share-modal`, trigger);
            }
            if (trigger.dataset.projectRoleMember) {
                const roleForm = host.querySelector(`#${kind}-role-modal form`);
                roleForm.elements.member_id.value = trigger.dataset.projectRoleMember;
                roleForm.elements.role.value = trigger.dataset.projectRole;
                roleForm.querySelector('[data-team-role-person]').textContent = trigger.dataset.projectPerson;
                openChild(`${kind}-role-modal`, trigger);
            }
            if (trigger.dataset.projectTeamAction) {
                const body = new FormData(); body.set('action', trigger.dataset.projectTeamAction);
                if (trigger.dataset.memberId) body.set('member_id', trigger.dataset.memberId);
                if (body.get('action') === 'remove') window.showConfirmModal({ title: isKanban ? (kind === 'section' ? 'Odebrać dostęp do tablicy?' : 'Odebrać dostęp do przestrzeni?') : isTask ? 'Odebrać dostęp do zadania?' : kind === 'section' ? 'Odebrać dostęp do grupy?' : 'Odebrać dostęp do projektu?', message: isKanban ? 'Osoba straci dostęp do tego prywatnego elementu Kanban, jego kart i plików. Zachowa pozostałe uprawnienia w Workspace.' : isTask ? 'Osoba straci dostęp do prywatnego zadania, jego podzadań i plików. Zachowa pozostałe uprawnienia w Workspace.' : kind === 'section' ? 'Osoba straci dostęp do prywatnej grupy, jej zadań i plików. Pozostanie członkiem projektu i Workspace.' : 'Osoba straci dostęp do prywatnego projektu, jego zadań i plików. Pozostanie członkiem Workspace.', confirmText: 'Odbierz dostęp', onConfirm: () => mutate(body) });
                else mutate(body);
            }
        }, options);
        form.addEventListener('keydown', event => {
            const selected = event.target.closest('[data-project-access-tab]');
            if (!selected || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const tabs = [...form.querySelectorAll('[data-project-access-tab]')].filter(node => !node.hidden);
            const index = tabs.indexOf(selected);
            const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
            selectTab(tabs[next].dataset.projectAccessTab, true);
        }, options);
        form.addEventListener('change', event => {
            const table = event.target.closest('[data-team-selection]'); if (!table) return;
            const all = table.querySelector('[data-team-select-all]'); const checks = [...table.querySelectorAll('[data-team-select]')];
            if (event.target === all) checks.forEach(input => { input.checked = all.checked; });
            all.checked = checks.every(input => input.checked); all.indeterminate = checks.some(input => input.checked) && !all.checked;
        }, options);
        form.addEventListener('invalid', () => selectTab('main'), { ...options, capture: true });
        host.addEventListener('submit', event => { if (event.target.matches('[data-project-team-form]')) { event.preventDefault(); mutate(new FormData(event.target), event.target); } }, options);
        document.addEventListener('ancore:task-modal-before-close', event => { if (pending && (event.target === main || host.contains(event.target))) event.preventDefault(); }, options);
        document.addEventListener('ancore:task-modal-closed', event => {
            if (host.contains(event.target)) { closePickers.forEach(close => close()); restoreBackground(); previousFocus?.isConnected && previousFocus.focus({preventScroll:true}); }
        }, options);
        form.addEventListener('ancore:task-team-updated', event => {
            version++; requestController?.abort(); display(event.detail);
        }, options);
        const id = form.elements[isTask ? 'task_pk' : `${kind}_id`].value;
        const access = JSON.parse(document.getElementById(`${kind}-access-data`)?.textContent || '{}')[id];
        if (isTask) load(form.dataset.taskTeamUrl);
        else if (id && access) { form.elements.visibility.disabled = !access.canManage; load(access.teamUrl); }
        return () => { version++; requestController?.abort(); controller.abort(); clearPickers(); restoreBackground(); };
    }
    function init() {
        cleanup();
        const cleanups = ['project', 'section', 'task'].map(initTeam);
        cleanup = () => cleanups.forEach(close => close());
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
