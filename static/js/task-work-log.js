(function () {
    if (window.ancoreTaskWorkLog) return;
    window.ancoreTaskWorkLog = true;
    let controller;
    const clock = new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'Europe/Warsaw', year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    });
    const localTime = instant => clock.format(instant).replace(' ', 'T');

    // Resolve Warsaw wall times independently of the browser's timezone.
    // Ambiguous/nonexistent times stay blank; Django reports the field error.
    function instantFor(value) {
        const wall = Date.parse(`${value}Z`);
        if (!Number.isFinite(wall)) return null;
        const offsets = new Set([-36, 36].map(hours => {
            const sample = wall + hours * 3600000;
            return Date.parse(`${localTime(sample)}Z`) - sample;
        }));
        const matches = [...offsets].map(offset => wall - offset).filter(instant => localTime(instant) === value);
        return matches.length === 1 ? matches[0] : null;
    }

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        const page = document.querySelector('.tasks-issue-page[data-task-app="tasks"]');
        if (!page) return;
        const panel = page.querySelector('#task-work-log');
        if (!panel) return;
        const selectedEntryIds = new Set([...panel.querySelectorAll('[data-work-log-select]:checked')].map(input => input.value));

        function syncSelection() {
            const inputs = [...panel.querySelectorAll('[data-work-log-select]')];
            const visibleIds = new Set(inputs.map(input => input.value));
            selectedEntryIds.forEach(id => { if (!visibleIds.has(id)) selectedEntryIds.delete(id); });
            inputs.forEach(input => {
                input.checked = selectedEntryIds.has(input.value);
                input.closest('[data-work-log-id]').classList.toggle('checked', input.checked);
            });
            const selectAll = panel.querySelector('[data-work-log-select-all]');
            if (selectAll) {
                selectAll.checked = inputs.length > 0 && selectedEntryIds.size === inputs.length;
                selectAll.indeterminate = selectedEntryIds.size > 0 && selectedEntryIds.size < inputs.length;
                selectAll.disabled = inputs.length === 0;
            }
        }
        panel.addEventListener('change', event => {
            const input = event.target;
            if (input.matches('[data-work-log-select-all]')) {
                selectedEntryIds.clear();
                if (input.checked) panel.querySelectorAll('[data-work-log-select]').forEach(item => selectedEntryIds.add(item.value));
            } else if (input.matches('[data-work-log-select]')) {
                if (input.checked) selectedEntryIds.add(input.value);
                else selectedEntryIds.delete(input.value);
            } else return;
            syncSelection();
        }, { signal });
        // Like the project directory, the whole checkbox column is clickable.
        panel.addEventListener('click', event => {
            if (event.target.closest('a, input, button, select, textarea')) return;
            const row = event.target.closest('[data-work-log-id]');
            const input = row?.querySelector('[data-work-log-select]');
            if (!input || !input.nextElementSibling) return;
            if (event.clientX >= row.getBoundingClientRect().left && event.clientX < input.nextElementSibling.getBoundingClientRect().left) input.click();
        }, { signal });
        syncSelection();
        const tabs = [...page.querySelectorAll('[data-task-tab]')];
        const modal = document.getElementById('task-work-log-modal');
        const form = modal?.querySelector('[data-work-log-form]');
        let pending = false;
        let inertElements = [];
        let returnEntryId = '';

        function selectTab(name, focus = false, updateUrl = true) {
            if (!tabs.some(tab => tab.dataset.taskTab === name)) name = 'main';
            tabs.forEach(tab => {
                const active = tab.dataset.taskTab === name;
                tab.setAttribute('aria-selected', String(active));
                tab.tabIndex = active ? 0 : -1;
                if (active && focus) tab.focus();
            });
            page.querySelectorAll('[data-task-tab-panel]').forEach(item => { item.hidden = item.dataset.taskTabPanel !== name; });
            page.querySelectorAll('[data-task-overview]').forEach(item => { item.hidden = name === 'history'; });
            page.querySelectorAll('[data-task-log-action]').forEach(item => { item.hidden = name !== 'work-log'; });
            if (updateUrl) {
                const url = new URL(window.location.href);
                if (name === 'main') url.searchParams.delete('tab');
                else url.searchParams.set('tab', name);
                window.history.replaceState(window.history.state, '', url);
            }
        }
        page.addEventListener('click', event => {
            const tab = event.target.closest('[data-task-tab]');
            if (tab) selectTab(tab.dataset.taskTab);
        }, { signal });
        page.addEventListener('invalid', event => {
            if (event.target.closest('[data-task-overview]')) selectTab('main');
        }, { signal, capture: true });
        page.addEventListener('keydown', event => {
            const tab = event.target.closest('[data-task-tab]');
            if (!tab || !['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
            event.preventDefault();
            const index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1
                : (tabs.indexOf(tab) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length;
            selectTab(tabs[index].dataset.taskTab, true);
        }, { signal });
        window.addEventListener('popstate', () => selectTab(new URL(window.location.href).searchParams.get('tab'), false, false), { signal });
        if (!form) return;

        function updateDuration() {
            const start = instantFor(form.elements['worklog-started_at'].value);
            const end = instantFor(form.elements['worklog-ended_at'].value);
            const minutes = start !== null && end !== null && end > start ? (end - start) / 60000 : null;
            form.elements['worklog-hours'].value = minutes === null ? '' : Math.floor(minutes / 60);
            form.elements['worklog-minutes'].value = minutes === null ? '' : minutes % 60;
        }
        function updateInterval() {
            const hours = form.elements['worklog-hours'];
            const minutes = form.elements['worklog-minutes'];
            const start = form.elements['worklog-started_at'];
            const end = form.elements['worklog-ended_at'];
            const total = (hours.valueAsNumber || 0) * 60 + (minutes.valueAsNumber || 0);
            if (!hours.validity.valid || !minutes.validity.valid || !Number.isSafeInteger(total) || total <= 0) {
                start.value = '';
                return;
            }
            if (!end.value) end.value = localTime(Date.now());
            const endInstant = instantFor(end.value);
            try {
                start.value = endInstant === null ? '' : localTime(endInstant - total * 60000);
            } catch (_) {
                start.value = '';
            }
        }
        function restoreBackground() {
            inertElements.forEach(element => { element.inert = false; });
            inertElements = [];
        }
        modal.addEventListener('ancore:task-modal-opened', () => {
            for (let node = modal; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
                        sibling.inert = true;
                        inertElements.push(sibling);
                    }
                });
            }
        }, { signal });
        modal.addEventListener('ancore:task-modal-before-close', event => {
            if (pending) event.preventDefault();
        }, { signal });
        modal.addEventListener('ancore:task-modal-closed', restoreBackground, { signal });
        signal.addEventListener('abort', restoreBackground, { once: true });
        form.addEventListener('input', event => {
            if (['worklog-started_at', 'worklog-ended_at'].includes(event.target.name)) {
                form.elements['worklog-calculation_mode'].value = 'interval';
                updateDuration();
            } else if (['worklog-hours', 'worklog-minutes'].includes(event.target.name)) {
                form.elements['worklog-calculation_mode'].value = 'duration';
                updateInterval();
            }
        }, { signal });

        page.addEventListener('click', event => {
            const open = event.target.closest('[data-open-work-log]');
            if (open && !pending) {
                const values = open.dataset.workLogValues ? JSON.parse(open.dataset.workLogValues) : {};
                returnEntryId = String(values.id || '');
                form.reset();
                form.elements.action.value = values.id ? 'edit_work_log' : 'add_work_log';
                form.elements.work_log_id.value = values.id || '';
                form.elements['worklog-started_at'].value = values.started_at || localTime(Date.now() - 3600000);
                form.elements['worklog-ended_at'].value = values.ended_at || localTime(Date.now());
                form.elements['worklog-description'].value = values.description || '';
                form.elements['worklog-calculation_mode'].value = 'duration';
                form.querySelectorAll('[aria-invalid]').forEach(field => field.removeAttribute('aria-invalid'));
                const errors = form.querySelector('.tasks-modal__errors');
                errors.replaceChildren();
                errors.hidden = true;
                modal.querySelector('h2').textContent = values.id ? 'Edytuj wpis czasu' : 'Dodaj czas';
                if (values.id && Number.isInteger(values.duration_minutes)) {
                    // A stored instant can fall in a repeated local hour during DST.
                    form.elements['worklog-hours'].value = Math.floor(values.duration_minutes / 60);
                    form.elements['worklog-minutes'].value = values.duration_minutes % 60;
                } else updateDuration();
                window.AncoreTaskModals.open(modal, form.elements['worklog-hours']);
            }
            const remove = event.target.closest('[data-delete-work-log]');
            if (remove && !pending) {
                const id = remove.dataset.deleteWorkLog;
                window.showConfirmModal({
                    title: 'Usuń wpis czasu', message: 'Czy na pewno chcesz usunąć ten wpis z dziennika pracy?',
                    confirmText: 'Usuń', cancelText: 'Anuluj',
                    onConfirm: () => {
                        const data = new FormData(form);
                        data.set('action', 'delete_work_log');
                        data.set('work_log_id', id);
                        send(data);
                    },
                });
            }
        }, { signal });

        async function send(data) {
            if (pending) return;
            pending = true;
            const submit = form.querySelector('[type="submit"]');
            submit.disabled = true;
            submit.textContent = 'Zapisywanie…';
            const deleting = data.get('action') === 'delete_work_log';
            data.set('work_log_page', data.get('action') === 'add_work_log' ? '1' : panel.querySelector('[data-work-log-page]').dataset.workLogPage);
            panel.setAttribute('aria-busy', 'true');
            const requestController = new AbortController();
            const abortRequest = () => requestController.abort();
            signal.addEventListener('abort', abortRequest, { once: true });
            const timeout = window.setTimeout(abortRequest, 15000);
            try {
                const response = await fetch(form.getAttribute('action'), {
                    method: 'POST', body: data, credentials: 'same-origin', signal: requestController.signal,
                    headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
                });
                const payload = await response.json();
                if (!response.ok || payload.status !== 'success') {
                    if (payload.form_html && !deleting) {
                        form.querySelector('[data-work-log-fields]').innerHTML = payload.form_html;
                        form.querySelector('[aria-invalid="true"]')?.focus();
                        return;
                    }
                    throw new Error(payload.message || 'Nie udało się zapisać wpisu. Spróbuj ponownie.');
                }
                panel.innerHTML = payload.work_log_html;
                syncSelection();
                window.AncoreIcons?.render(panel);
                document.dispatchEvent(new CustomEvent('ancore:modals-loaded'));
                window.prependTaskDetailActivityItems?.(payload.activity_html);
                pending = false;
                window.AncoreTaskModals.close(modal);
                const returnTarget = returnEntryId && panel.querySelector(`[data-work-log-id="${returnEntryId}"] [data-row-actions-toggle]`);
                (returnTarget || page.querySelector('[data-open-work-log]'))?.focus({ preventScroll: true });
                window.showNotification?.(payload.message, 'success');
                const url = new URL(window.location.href);
                url.searchParams.set('work_log_page', panel.querySelector('[data-work-log-page]').dataset.workLogPage);
                window.history.replaceState(window.history.state, '', url);
            } catch (error) {
                if (signal.aborted) return;
                const message = 'Nie udało się zapisać wpisu. Sprawdź połączenie i spróbuj ponownie.';
                if (!deleting) {
                    const errors = form.querySelector('.tasks-modal__errors');
                    errors.textContent = message;
                    errors.hidden = false;
                }
                window.showNotification?.(message, 'error');
            } finally {
                window.clearTimeout(timeout);
                signal.removeEventListener('abort', abortRequest);
                pending = false;
                panel.removeAttribute('aria-busy');
                submit.disabled = false;
                submit.textContent = 'Zapisz wpis';
            }
        }
        form.addEventListener('submit', event => {
            event.preventDefault();
            send(new FormData(form));
        }, { signal });
        if (modal.hasAttribute('data-open-on-load')) {
            selectTab('work-log');
            window.AncoreTaskModals.open(modal, form.querySelector('[aria-invalid="true"]') || form.elements['worklog-started_at']);
        }
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
