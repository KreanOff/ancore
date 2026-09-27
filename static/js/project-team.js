(function () {
    if (window.ancoreProjectTeam) return;
    window.ancoreProjectTeam = true;
    let cleanup = () => {};
    function init() {
        cleanup();
        const form = document.getElementById('project-rename-form');
        const host = document.querySelector('[data-project-team-modal-host]');
        if (!form || !host) return;
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
            const tabs = [...form.querySelectorAll('[data-project-access-tab]')].filter(node => !node.hidden);
            if (!tabs.some(node => node.dataset.projectAccessTab === name)) name = 'main';
            tab = name;
            tabs.forEach(node => {
                const selected = node.dataset.projectAccessTab === name;
                node.setAttribute('aria-selected', String(selected)); node.tabIndex = selected ? 0 : -1;
                if (selected && focus) node.focus();
            });
            form.querySelectorAll('[data-project-access-panel]').forEach(node => { node.hidden = node.dataset.projectAccessPanel !== name; });
            form.querySelector('#project-rename-submit').hidden = name !== 'main' || form.dataset.projectReadonly === 'true';
            form.querySelector('footer [data-close-modal]').textContent = name === 'main' && form.dataset.projectReadonly !== 'true' ? 'Anuluj' : 'Zamknij';
        }
        function clearPickers() {
            closePickers.forEach(close => close()); closePickers = [];
            pickerController?.abort();
        }
        function display(data) {
            clearPickers();
            form.querySelector('[data-project-team-members]').innerHTML = data.members;
            form.querySelector('[data-project-team-invitations]').innerHTML = data.invitations;
            form.querySelector('[data-project-access-tab="invitations"]').hidden = !data.can_manage;
            host.innerHTML = data.modals;
            host.querySelectorAll('form').forEach(node => { node.action = url; });
            window.AncoreIcons?.render(form); window.AncoreIcons?.render(host);
            window.AncoreCustomSelect?.refresh(host);
            document.dispatchEvent(new CustomEvent('ancore:modals-loaded', { detail: { root: host } }));
            pickerController = new AbortController();
            closePickers = [...host.querySelectorAll('[data-team-invite-picker]')].map(picker =>
                window.AncoreTeamInvitationPicker.init(picker, { signal: pickerController.signal }));
            selectTab(tab);
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
                    throw new Error(messages.join(' ') || data.error || 'Nie udało się zapisać zmian. Odśwież projekt i spróbuj ponownie.');
                }
                return data;
            } finally { clearTimeout(timer); }
        }
        async function load(teamUrl) {
            const current = ++version;
            requestController?.abort(); clearPickers();
            url = teamUrl; selectTab('main'); errorBox.hidden = true;
            form.querySelector('[data-project-access-tab="invitations"]').hidden = true;
            form.querySelector('[data-project-team-members]').textContent = 'Ładowanie członków…';
            form.querySelector('[data-project-team-invitations]').replaceChildren(); host.replaceChildren();
            if (!url) return;
            try { const data = await request(); if (current === version) display(data); }
            catch (error) { if (current === version && !controller.signal.aborted) { errorBox.textContent = 'Nie udało się pobrać członków. Zamknij i ponownie otwórz projekt.'; errorBox.hidden = false; } }
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
                if (body.get('action') === 'invite' || body.get('action') === 'cancel') tab = 'invitations';
                display(data);
                form.querySelector(`[data-project-access-tab="${tab}"]`)?.focus();
                window.showNotification?.('Zmiany zapisane.', 'success');
            } catch (error) {
                if (!controller.signal.aborted) { errors.textContent = error.message; errors.hidden = false; }
            } finally { pending = false; controls.forEach(([node, disabled]) => { node.disabled = disabled; }); }
        }
        document.addEventListener('ancore:project-team-selected', event => { if (event.target === form) load(event.detail.url); }, options);
        form.addEventListener('click', event => {
            const trigger = event.target.closest('button'); if (!trigger || pending) return;
            if (trigger.dataset.projectAccessTab) selectTab(trigger.dataset.projectAccessTab);
            if (trigger.hasAttribute('data-project-invite-open')) {
                host.querySelector('[name="email"]').value = '';
                host.querySelector('[data-team-invite-selected]').hidden = true;
                openChild('project-invite-modal', trigger);
            }
            if (trigger.dataset.projectRoleMember) {
                const roleForm = host.querySelector('#project-role-modal form');
                roleForm.elements.member_id.value = trigger.dataset.projectRoleMember;
                roleForm.elements.role.value = trigger.dataset.projectRole;
                roleForm.querySelector('[data-team-role-person]').textContent = trigger.dataset.projectPerson;
                openChild('project-role-modal', trigger);
            }
            if (trigger.dataset.projectTeamAction) {
                const body = new FormData(); body.set('action', trigger.dataset.projectTeamAction);
                if (trigger.dataset.memberId) body.set('member_id', trigger.dataset.memberId);
                if (trigger.dataset.invitationId) body.set('invitation_id', trigger.dataset.invitationId);
                if (body.get('action') === 'remove') window.showConfirmModal({ title: 'Odebrać dostęp do projektu?', message: 'Osoba straci dostęp do prywatnego projektu, jego zadań i plików. Pozostanie członkiem Workspace.', confirmText: 'Odbierz dostęp', onConfirm: () => mutate(body) });
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
            if (event.target.matches('[data-project-response-modal]')) { restoreBackground(); const current = new URL(location.href); current.searchParams.delete('project_invitation'); history.replaceState(history.state, '', current); }
        }, options);
        const response = document.querySelector('[data-project-response-modal].is-open');
        if (response) protectBackground(response);
        const id = form.elements.project_id.value;
        const access = JSON.parse(document.getElementById('project-access-data')?.textContent || '{}')[id];
        if (id && access) { form.elements.visibility.disabled = !access.canManage; load(access.teamUrl); }
        cleanup = () => { version++; requestController?.abort(); controller.abort(); clearPickers(); restoreBackground(); };
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
