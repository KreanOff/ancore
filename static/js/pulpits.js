(function () {
    if (window.ancorePulpitsLoaded) return;
    window.ancorePulpitsLoaded = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        const page = document.querySelector('[data-pulpits-page]');
        const host = document.querySelector('[data-pulpit-modal-host]');
        if (!page || !host) return;
        let pending = false;
        let discard = false;
        let initial = '';
        let previousFocus;
        let background = [];
        const modal = () => host.querySelector('[data-pulpit-modal]');
        const values = () => JSON.stringify([...new FormData(host.querySelector('form'))].filter(([name]) => name !== 'csrfmiddlewaretoken'));
        const dirty = () => modal() && values() !== initial;

        function restoreBackground() {
            background.forEach(element => { element.inert = false; });
            background = [];
        }

        function disableBackground() {
            for (let node = host; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
                        sibling.inert = true;
                        background.push(sibling);
                    }
                });
            }
        }

        async function request(url, options = {}) {
            const response = await fetch(url, {
                ...options, credentials: 'same-origin',
                signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
                headers: { 'X-Pulpit-Modal': 'true' },
            });
            if (response.redirected || (!response.ok && response.status !== 400)) throw new Error('Pulpit request failed');
            return response.json();
        }

        function display(html, preserveInitial = false) {
            restoreBackground();
            host.innerHTML = html;
            if (!modal()) throw new Error('Missing pulpit form');
            if (!preserveInitial) initial = values();
            window.AncoreIcons?.render(host);
            window.AncoreTaskModals.open(modal(), host.querySelector('[aria-invalid="true"], input:not([type="hidden"])'));
            disableBackground();
            updateFields();
        }

        function updateFields() {
            const visibility = host.querySelector('[name="visibility"]');
            const sharing = host.querySelector('[data-pulpit-field="shared_with"]');
            if (sharing && visibility) sharing.hidden = visibility.value !== 'selected';
            const kind = host.querySelector('[name="kind"]')?.value;
            if (!kind) return;
            const grouping = host.querySelector('[data-pulpit-field="group_by"]');
            const limit = host.querySelector('[data-pulpit-field="limit"]');
            grouping.hidden = kind !== 'statistics';
            limit.hidden = !['results', 'assigned', 'activity'].includes(kind);
        }

        async function refresh(url) {
            if (window.AncoreApp?.navigate) await window.AncoreApp.navigate(url, { replace: true });
            else window.location.href = url;
        }

        document.addEventListener('click', async event => {
            const trigger = event.target.closest('[data-pulpit-open]');
            if (!trigger || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            if (pending || modal()) return;
            pending = true;
            previousFocus = trigger.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || trigger;
            trigger.setAttribute('aria-busy', 'true');
            try {
                const result = await request(trigger.href);
                if (!signal.aborted) display(result.html);
            } catch (error) {
                if (!signal.aborted) window.showNotification?.('Nie udało się otworzyć pulpitu. Spróbuj ponownie.', 'error');
            } finally {
                pending = false;
                trigger.removeAttribute('aria-busy');
            }
        }, { signal, capture: true });

        host.addEventListener('submit', async event => {
            const form = event.target.closest('[data-pulpit-form]');
            if (!form) return;
            event.preventDefault();
            if (pending) return;
            const body = new FormData(form);
            const controls = [...form.querySelectorAll('button, input, select, textarea')].map(control => [control, control.disabled]);
            const errorBox = form.querySelector('[data-pulpit-error]');
            pending = true;
            controls.forEach(([control]) => { control.disabled = true; });
            form.setAttribute('aria-busy', 'true');
            errorBox.hidden = true;
            try {
                const result = await request(form.action, { method: 'POST', body });
                if (signal.aborted) return;
                if (result.saved) {
                    pending = false;
                    discard = true;
                    window.AncoreTaskModals.close(modal());
                    await refresh(result.url);
                    window.showNotification?.('Zmiany zapisane.', 'success');
                } else display(result.html, true);
            } catch (error) {
                if (!signal.aborted) {
                    errorBox.textContent = 'Nie udało się zapisać pulpitu. Sprawdź połączenie i spróbuj ponownie.';
                    errorBox.hidden = false;
                }
            } finally {
                pending = false;
                controls.forEach(([control, disabled]) => { control.disabled = disabled; });
                window.AncoreCustomSelect?.refresh(form);
                form.removeAttribute('aria-busy');
            }
        }, { signal });

        page.addEventListener('submit', event => {
            const form = event.target.closest('[data-pulpit-action]');
            if (!form) return;
            event.preventDefault();
            if (pending) return;
            const execute = async () => {
                if (signal.aborted || pending) return;
                pending = true;
                const button = form.querySelector('button');
                button.disabled = true;
                try {
                    const result = await request(form.action, { method: 'POST', body: new FormData(form) });
                    if (!signal.aborted) await refresh(result.url);
                } catch (error) {
                    if (!signal.aborted) window.showNotification?.('Nie udało się zapisać zmiany. Spróbuj ponownie.', 'error');
                } finally { pending = false; button.disabled = false; }
            };
            if (form.dataset.confirmTitle) window.showConfirmModal({
                title: form.dataset.confirmTitle,
                message: window.escapeHtmlForModal(`Usunąć „${form.dataset.confirmName}”?`),
                confirmText: 'Usuń', cancelText: 'Anuluj', confirmClass: 'btn-danger', onConfirm: execute,
            });
            else execute();
        }, { signal });

        host.addEventListener('ancore:task-modal-before-close', event => {
            if (pending) { event.preventDefault(); return; }
            if (discard || !dirty()) return;
            event.preventDefault();
            window.showConfirmModal({
                title: 'Niezapisane zmiany', message: 'Zamknąć formularz bez zapisania zmian?',
                confirmText: 'Zamknij bez zapisu', cancelText: 'Wróć do edycji',
                onConfirm: () => {
                    if (signal.aborted) return;
                    discard = true;
                    window.AncoreTaskModals.close(modal());
                },
            });
        }, { signal });
        host.addEventListener('ancore:task-modal-closed', () => {
            restoreBackground();
            host.replaceChildren();
            discard = false;
            previousFocus?.focus({ preventScroll: true });
            const list = new URL(page.dataset.pulpitListUrl, window.location.origin);
            if (window.location.pathname !== list.pathname) window.history.replaceState(window.history.state, '', list.href);
        }, { signal });
        document.addEventListener('ancore:before-navigate', event => {
            if (!modal() || discard) return;
            if (pending || dirty()) {
                event.preventDefault();
                window.AncoreTaskModals.close(modal());
            }
        }, { signal });
        window.addEventListener('beforeunload', event => {
            if (dirty()) { event.preventDefault(); event.returnValue = ''; }
        }, { signal });
        signal.addEventListener('abort', restoreBackground, { once: true });
        initArrangement(page, signal);
        page.querySelector('[data-pulpit-refresh]')?.addEventListener('click', () => refresh(page.dataset.pulpitListUrl), { signal });
        page.querySelector('[data-pulpit-search]')?.addEventListener('submit', event => {
            event.preventDefault();
            const form = event.currentTarget;
            refresh(form.action + '?' + new URLSearchParams(new FormData(form)));
        }, { signal });
        page.querySelectorAll('[data-pulpit-management-filters] select').forEach(select => {
            select.addEventListener('change', () => select.form.requestSubmit(), { signal });
        });
        host.addEventListener('change', updateFields, { signal });
        if (modal()) display(host.innerHTML);
    }
    function initArrangement(page, signal) {
        const grid = page.querySelector('[data-pulpit-grid][data-editable]');
        if (!grid) return;
        const layoutSelect = page.querySelector('[data-pulpit-layout]');
        const errorBox = page.querySelector('[data-pulpit-page-error]');
        let saving = false;
        let dragged;
        let snapshot;
        const columns = () => [...grid.querySelectorAll('[data-pulpit-column]')];
        const capture = () => ({ layout: grid.dataset.layout, columns: columns().map(column => [...column.children]) });
        function setColumns(layout, content) {
            const count = layout === 'single' ? 1 : layout === 'three' ? 3 : 2;
            while (columns().length < count) {
                const column = document.createElement('section');
                column.className = 'pulpit-column';
                column.dataset.pulpitColumn = columns().length;
                column.setAttribute('aria-label', `Kolumna ${columns().length + 1}`);
                grid.append(column);
            }
            if (content) content.forEach((items, index) => items.forEach(item => columns()[Math.min(index, count - 1)].append(item)));
            columns().slice(count).forEach(column => {
                [...column.children].forEach(gadget => columns()[count - 1].append(gadget));
                column.remove();
            });
            grid.className = 'pulpit-grid pulpit-grid--' + layout;
            grid.dataset.layout = layout;
            layoutSelect.value = layout;
            window.AncoreCustomSelect?.refresh(layoutSelect.closest('.ancore-custom-select') || layoutSelect.parentElement);
        }
        async function save(before, focus) {
            saving = true;
            layoutSelect.disabled = true;
            window.AncoreCustomSelect?.refresh(layoutSelect.closest('.ancore-custom-select') || layoutSelect.parentElement);
            grid.setAttribute('aria-busy', 'true');
            errorBox.hidden = true;
            try {
                const response = await fetch(page.dataset.pulpitArrangeUrl, {
                    method: 'POST', credentials: 'same-origin',
                    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': page.querySelector('[name="csrfmiddlewaretoken"]').value },
                    body: JSON.stringify({ layout: grid.dataset.layout, revision: Number(page.dataset.pulpitRevision), columns: columns().map(column => [...column.querySelectorAll('[data-pulpit-gadget]')].map(gadget => Number(gadget.dataset.pulpitGadget))) }),
                });
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'Nie udało się zapisać układu.');
                if (!signal.aborted) {
                    page.dataset.pulpitRevision = result.revision;
                    page.querySelector('[data-pulpit-status]').textContent = 'Układ pulpitu zapisany.';
                }
            } catch (error) {
                if (!signal.aborted) {
                    setColumns(before.layout, before.columns);
                    errorBox.textContent = error.message || 'Nie udało się zapisać układu. Odśwież stronę i spróbuj ponownie.';
                    errorBox.hidden = false;
                }
            } finally {
                saving = false;
                layoutSelect.disabled = false;
                window.AncoreCustomSelect?.refresh(layoutSelect.closest('.ancore-custom-select') || layoutSelect.parentElement);
                grid.removeAttribute('aria-busy');
                focus?.focus({ preventScroll: true });
            }
        }
        layoutSelect.addEventListener('change', () => {
            if (saving) { layoutSelect.value = grid.dataset.layout; return; }
            const before = capture();
            setColumns(layoutSelect.value);
            save(before, layoutSelect);
        }, { signal });
        grid.addEventListener('click', event => {
            const button = event.target.closest('[data-pulpit-move]');
            if (!button || saving) return;
            const gadget = button.closest('[data-pulpit-gadget]');
            const column = gadget.parentElement;
            const before = capture();
            const direction = button.dataset.pulpitMove;
            const sibling = direction === 'up' ? gadget.previousElementSibling : gadget.nextElementSibling;
            if (direction === 'column') {
                if (columns().length < 2) return;
                columns()[(columns().indexOf(column) + 1) % columns().length].append(gadget);
            } else if (sibling) column.insertBefore(gadget, direction === 'up' ? sibling : sibling.nextElementSibling);
            else return;
            button.closest('[popover]')?.hidePopover();
            save(before, gadget.querySelector('[data-row-actions-toggle]'));
        }, { signal });
        grid.addEventListener('dragstart', event => {
            if (saving || !event.target.closest('[data-pulpit-drag]')) { event.preventDefault(); return; }
            dragged = event.target.closest('[data-pulpit-gadget]');
            snapshot = capture();
            dragged.classList.add('is-dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', dragged.dataset.pulpitGadget);
        }, { signal });
        grid.addEventListener('dragover', event => {
            const column = event.target.closest('[data-pulpit-column]');
            if (!dragged || !column || saving) return;
            event.preventDefault();
            columns().forEach(item => item.classList.toggle('is-drop-target', item === column));
            event.dataTransfer.dropEffect = 'move';
        }, { signal });
        function clearDrag() {
            dragged?.classList.remove('is-dragging');
            columns().forEach(column => column.classList.remove('is-drop-target'));
            dragged = null;
        }
        grid.addEventListener('drop', event => {
            const column = event.target.closest('[data-pulpit-column]');
            if (!dragged || !column || saving) return;
            event.preventDefault();
            const target = event.target.closest('[data-pulpit-gadget]');
            if (target && target !== dragged) {
                const rect = target.getBoundingClientRect();
                column.insertBefore(dragged, event.clientY < rect.top + rect.height / 2 ? target : target.nextElementSibling);
            } else if (!target) column.append(dragged);
            const focus = dragged.querySelector('[data-pulpit-drag]');
            clearDrag();
            save(snapshot, focus);
        }, { signal });
        grid.addEventListener('dragend', clearDrag, { signal });
        document.addEventListener('ancore:before-navigate', event => { if (saving) event.preventDefault(); }, { signal });
    }
    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
