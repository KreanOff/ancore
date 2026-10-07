(function () {
    if (window.ancorePulpitsLoaded) return;
    window.ancorePulpitsLoaded = true;
    let controller;

    function updateFormFields(root) {
        const visibility = root.querySelector('[name="visibility"]');
        const sharing = root.querySelector('[data-pulpit-field="shared_with"]');
        if (sharing && visibility) sharing.hidden = visibility.value !== 'selected';
        const kindField = root.querySelector('[name="kind"]');
        if (!kindField) return;
        const kind = kindField.value;
        const previewKind = ['assigned', 'statistics', 'results', 'summary', 'activity'].includes(kind) ? kind : '';
        root.querySelectorAll('[data-pulpit-preview-kind]').forEach(preview => {
            preview.hidden = preview.dataset.pulpitPreviewKind !== previewKind;
        });
        const grouping = root.querySelector('[data-pulpit-field="group_by"]');
        const limit = root.querySelector('[data-pulpit-field="limit"]');
        grouping.hidden = kind !== 'statistics';
        limit.hidden = !['results', 'assigned', 'activity'].includes(kind);
    }

    function initEditForm(form, signal) {
        if (!form) return;
        const values = () => JSON.stringify([...new FormData(form)].filter(([name]) => name !== 'csrfmiddlewaretoken'));
        const initial = values();
        let submitting = false;
        let discard = false;
        const dirty = () => !discard && (form.dataset.pulpitUnsaved === 'true' || values() !== initial);
        updateFormFields(form);
        form.addEventListener('change', () => updateFormFields(form), { signal });
        form.querySelector('[aria-invalid="true"]')?.focus({ preventScroll: true });
        form.addEventListener('submit', event => {
            if (submitting) { event.preventDefault(); return; }
            submitting = true;
            form.setAttribute('aria-busy', 'true');
        }, { signal });
        window.addEventListener('pageshow', event => {
            if (!event.persisted) return;
            submitting = false;
            form.removeAttribute('aria-busy');
        }, { signal });
        document.addEventListener('ancore:before-navigate', event => {
            if (submitting) { event.preventDefault(); return; }
            if (!dirty()) return;
            event.preventDefault();
            if (document.querySelector('.confirm-modal-overlay')) return;
            window.showConfirmModal({
                title: 'Niezapisane zmiany', message: 'Opuścić edycję pulpitu bez zapisania zmian?',
                confirmText: 'Wyjdź bez zapisu', cancelText: 'Wróć do edycji',
                onConfirm: () => {
                    if (signal.aborted) return;
                    discard = true;
                    window.AncoreApp.navigate(event.detail.url);
                },
            });
        }, { signal });
        window.addEventListener('beforeunload', event => {
            if (!submitting && dirty()) { event.preventDefault(); event.returnValue = ''; }
        }, { signal });
    }

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        const page = document.querySelector('[data-pulpits-page]');
        const host = document.querySelector('[data-pulpit-modal-host]');
        if (!page || !host) return;
        initEditForm(page.querySelector('[data-pulpit-edit-form]'), signal);
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
            updateFormFields(host);
        }

        async function refresh(url) {
            if (window.AncoreApp?.navigate) await window.AncoreApp.navigate(url, { replace: true });
            else window.location.href = url;
        }

        document.addEventListener('click', async event => {
            const trigger = event.target.closest('[data-pulpit-open]');
            if (!trigger || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            if (pending || modal() || page.dataset.pulpitSaving === 'true') return;
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
            if (pending || page.dataset.pulpitSaving === 'true') return;
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
            if (pending || page.dataset.pulpitSaving === 'true') return;
            const execute = async () => {
                if (signal.aborted || pending || page.dataset.pulpitSaving === 'true') return;
                pending = true;
                page.dataset.pulpitSaving = 'true';
                page.dispatchEvent(new Event('pulpit:busy'));
                const button = form.querySelector('button');
                button.disabled = true;
                try {
                    const result = await request(form.action, { method: 'POST', body: new FormData(form) });
                    delete page.dataset.pulpitSaving;
                    page.dispatchEvent(new Event('pulpit:busy'));
                    if (!signal.aborted) await refresh(result.url);
                } catch (error) {
                    if (!signal.aborted) window.showNotification?.('Nie udało się zapisać zmiany. Spróbuj ponownie.', 'error');
                } finally {
                    pending = false;
                    button.disabled = false;
                    delete page.dataset.pulpitSaving;
                    page.dispatchEvent(new Event('pulpit:busy'));
                }
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
        initCatalog(page, signal);
        page.querySelector('[data-pulpit-refresh]')?.addEventListener('click', () => {
            if (!pending && page.dataset.pulpitSaving !== 'true') refresh(page.dataset.pulpitListUrl);
        }, { signal });
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
    function initCatalog(page, signal) {
        const catalog = page.querySelector('[data-pulpit-catalog]');
        if (!catalog) return;
        const search = catalog.querySelector('[data-pulpit-catalog-search]');
        const errorBox = catalog.querySelector('[data-pulpit-catalog-error]');
        const status = catalog.querySelector('[data-pulpit-catalog-status]');
        const items = [...catalog.querySelectorAll('[data-pulpit-catalog-item]')];
        const key = 'ancore:pulpit-catalog:' + new URL(page.dataset.pulpitListUrl, location.origin).pathname;
        let category = 'all';
        let opener;
        function persist() {
            try { sessionStorage.setItem(key, JSON.stringify({ open: !catalog.hidden, category, query: search.value })); } catch (_) { /* Optional UI preference. */ }
        }
        function setOpen(open, focus = true) {
            catalog.hidden = !open;
            page.classList.toggle('has-catalog', open);
            page.querySelectorAll('[data-pulpit-catalog-toggle]').forEach(button => button.setAttribute('aria-expanded', String(open)));
            if (focus) (open ? search : opener?.isConnected ? opener : page.querySelector('[data-pulpit-catalog-toggle]'))?.focus({ preventScroll: true });
            persist();
        }
        function updateLimit() {
            const atLimit = Number(page.dataset.pulpitCount) >= Number(page.dataset.pulpitMax);
            catalog.querySelector('[data-pulpit-catalog-limit]').hidden = !atLimit;
            catalog.querySelectorAll('[data-pulpit-quick-add]').forEach(button => {
                button.disabled = atLimit || page.dataset.pulpitSaving === 'true';
            });
        }
        const normalize = text => text.toLocaleLowerCase('pl').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/ł/g, 'l');
        function filter() {
            const query = normalize(search.value.trim());
            let count = 0;
            items.forEach(item => {
                item.hidden = (category !== 'all' && item.dataset.category !== category) || !normalize(item.querySelector('.pulpit-catalog-item-copy').textContent).includes(query);
                if (!item.hidden) count++;
            });
            catalog.querySelector('[data-pulpit-catalog-empty]').hidden = count > 0;
            status.textContent = `Pasujące gadżety: ${count}.`;
            catalog.querySelectorAll('[data-pulpit-category]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.pulpitCategory === category)));
            persist();
        }
        search.addEventListener('input', filter, { signal });
        page.addEventListener('click', async event => {
            const toggle = event.target.closest('[data-pulpit-catalog-toggle]');
            if (toggle) {
                if (event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
                event.preventDefault();
                opener = toggle;
                setOpen(catalog.hidden);
                return;
            }
            if (event.target.closest('[data-pulpit-catalog-close]')) { setOpen(false); return; }
            const filterButton = event.target.closest('[data-pulpit-category]');
            if (filterButton) { category = filterButton.dataset.pulpitCategory; filter(); return; }
            if (event.target.closest('[data-pulpit-catalog-reset]')) { search.value = ''; category = 'all'; filter(); search.focus(); return; }
            const button = event.target.closest('[data-pulpit-quick-add]');
            if (!button || page.dataset.pulpitSaving === 'true' || document.querySelector('[data-pulpit-modal]')) return;
            page.dataset.pulpitSaving = 'true';
            page.dispatchEvent(new Event('pulpit:busy'));
            updateLimit();
            errorBox.hidden = true;
            button.textContent = 'Dodawanie…';
            button.setAttribute('aria-busy', 'true');
            status.textContent = 'Dodawanie gadżetu…';
            let errorMessage = 'Nie udało się dodać gadżetu. Sprawdź połączenie i odśwież pulpit przed ponowieniem.';
            try {
                const response = await fetch(page.dataset.pulpitQuickAddUrl, {
                    method: 'POST', credentials: 'same-origin',
                    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': page.querySelector('[name="csrfmiddlewaretoken"]').value },
                    body: JSON.stringify({ kind: button.dataset.pulpitQuickAdd, revision: Number(page.dataset.pulpitRevision) }),
                });
                const result = await response.json();
                if (!response.ok) { errorMessage = result.error || errorMessage; throw new Error(errorMessage); }
                if (signal.aborted) return;
                const column = page.querySelector(`[data-pulpit-column="${result.column}"]`);
                column.insertAdjacentHTML('beforeend', result.html);
                page.dataset.pulpitRevision = result.revision;
                page.dataset.pulpitCount = result.gadget_count;
                page.dispatchEvent(new Event('pulpit:changed'));
                window.AncoreIcons?.render(column);
                document.dispatchEvent(new Event('ancore:modals-loaded'));
                status.textContent = 'Gadżet dodany. Możesz dodać następny lub skonfigurować jego filtry.';
                page.querySelector('[data-pulpit-status]').textContent = 'Gadżet dodany i zapisany.';
            } catch (error) {
                if (!signal.aborted) {
                    errorBox.textContent = errorMessage;
                    errorBox.hidden = false;
                    status.textContent = 'Gadżet nie został dodany.';
                }
            } finally {
                delete page.dataset.pulpitSaving;
                button.textContent = 'Dodaj';
                button.removeAttribute('aria-busy');
                updateLimit();
                page.dispatchEvent(new Event('pulpit:busy'));
            }
        }, { signal });
        catalog.addEventListener('keydown', event => {
            if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); setOpen(false); }
        }, { signal });
        page.addEventListener('pulpit:busy', updateLimit, { signal });
        // Keep the catalog/filter state when configuration returns to this editor.
        try {
            const stored = JSON.parse(sessionStorage.getItem(key) || 'null');
            if (stored) { category = stored.category || 'all'; search.value = stored.query || ''; setOpen(Boolean(stored.open), false); }
        } catch (_) { /* Storage may be disabled. */ }
        signal.addEventListener('abort', persist, { once: true });
        filter();
        updateLimit();
    }
    function initArrangement(page, signal) {
        const grid = page.querySelector('[data-pulpit-grid][data-editable]');
        if (!grid) return;
        const errorBox = page.querySelector('[data-pulpit-page-error]');
        const layoutSelect = page.querySelector('[data-pulpit-layout]');
        const status = page.querySelector('[data-pulpit-status]');
        let saving = false;
        let dragged;
        let snapshot;
        const columns = () => [...grid.querySelectorAll('[data-pulpit-column]')];
        const gadgets = column => [...column.querySelectorAll('[data-pulpit-gadget]')];
        const capture = () => ({ layout: grid.dataset.layout, columns: columns().map(gadgets) });
        function updateControls() {
            const busy = saving || page.dataset.pulpitSaving === 'true';
            columns().forEach(column => {
                const empty = gadgets(column).length === 0;
                column.classList.toggle('is-empty', empty);
                const placeholder = column.querySelector('[data-pulpit-placeholder]');
                if (!empty) placeholder?.remove();
                else if (!placeholder) {
                    const content = document.createElement('div');
                    content.className = 'pulpit-column-placeholder';
                    content.dataset.pulpitPlaceholder = '';
                    content.innerHTML = '<i data-icon="layout-dashboard" aria-hidden="true"></i><span>Przeciągnij gadżet do tej kolumny</span><button type="button" class="tasks-filter-button" data-pulpit-catalog-toggle aria-controls="pulpit-catalog" aria-expanded="false">Dodaj nowy gadżet</button>';
                    content.querySelector('button').setAttribute('aria-expanded', String(page.classList.contains('has-catalog')));
                    column.append(content);
                    window.AncoreIcons?.render(content);
                }
            });
            grid.querySelectorAll('[data-pulpit-move]').forEach(button => {
                const gadget = button.closest('[data-pulpit-gadget]');
                button.disabled = busy || (button.dataset.pulpitMove === 'up' && !gadget.previousElementSibling)
                    || (button.dataset.pulpitMove === 'down' && !gadget.nextElementSibling)
                    || (button.dataset.pulpitMove === 'column' && columns().length < 2);
            });
            if (layoutSelect) {
                layoutSelect.value = grid.dataset.layout;
                layoutSelect.disabled = busy;
                window.AncoreCustomSelect?.refresh(page);
            }
            const preview = page.querySelector('[data-pulpit-layout-preview]');
            if (preview) preview.className = 'pulpit-layout-preview pulpit-layout-preview--' + grid.dataset.layout;
            page.querySelectorAll('[data-pulpit-layout-choice]').forEach(button => {
                button.disabled = busy;
                button.setAttribute('aria-pressed', String(button.dataset.pulpitLayoutChoice === grid.dataset.layout));
            });
        }
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
                gadgets(column).forEach(gadget => columns()[count - 1].append(gadget));
                column.remove();
            });
            grid.className = 'pulpit-grid pulpit-grid--' + layout;
            grid.dataset.layout = layout;
            updateControls();
        }
        async function save(before, focus) {
            saving = true;
            page.dataset.pulpitSaving = 'true';
            page.dispatchEvent(new Event('pulpit:busy'));
            grid.setAttribute('aria-busy', 'true');
            errorBox.hidden = true;
            status.textContent = 'Zapisywanie układu…';
            updateControls();
            let errorMessage = 'Nie udało się zapisać układu. Sprawdź połączenie i odśwież pulpit przed kolejną zmianą.';
            try {
                const response = await fetch(page.dataset.pulpitArrangeUrl, {
                    method: 'POST', credentials: 'same-origin',
                    signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': page.querySelector('[name="csrfmiddlewaretoken"]').value },
                    body: JSON.stringify({ layout: grid.dataset.layout, revision: Number(page.dataset.pulpitRevision), columns: columns().map(column => [...column.querySelectorAll('[data-pulpit-gadget]')].map(gadget => Number(gadget.dataset.pulpitGadget))) }),
                });
                const result = await response.json();
                if (!response.ok) {
                    errorMessage = result.error || errorMessage;
                    throw new Error(errorMessage);
                }
                if (!signal.aborted) {
                    page.dataset.pulpitRevision = result.revision;
                    status.textContent = 'Układ pulpitu zapisany.';
                }
            } catch (error) {
                if (!signal.aborted) {
                    setColumns(before.layout, before.columns);
                    errorBox.textContent = errorMessage;
                    errorBox.hidden = false;
                    status.textContent = 'Układ nie został zapisany. Przywrócono poprzedni układ.';
                }
            } finally {
                saving = false;
                delete page.dataset.pulpitSaving;
                page.dispatchEvent(new Event('pulpit:busy'));
                grid.removeAttribute('aria-busy');
                updateControls();
                focus?.focus({ preventScroll: true });
            }
        }
        function changeLayout(layout) {
            if (page.dataset.pulpitSaving === 'true' || layout === grid.dataset.layout) return;
            const before = capture();
            setColumns(layout);
            save(before, page.querySelector('.pulpit-layout-control button'));
        }
        layoutSelect?.addEventListener('change', () => changeLayout(layoutSelect.value), { signal });
        page.addEventListener('click', event => {
            const button = event.target.closest('[data-pulpit-layout-choice]');
            if (button) changeLayout(button.dataset.pulpitLayoutChoice);
        }, { signal });
        page.addEventListener('pulpit:changed', updateControls, { signal });
        page.addEventListener('pulpit:busy', updateControls, { signal });
        updateControls();
        grid.addEventListener('click', event => {
            const button = event.target.closest('[data-pulpit-move]');
            if (!button || page.dataset.pulpitSaving === 'true') return;
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
            if (page.dataset.pulpitSaving === 'true' || !event.target.closest('[data-pulpit-drag]')) { event.preventDefault(); return; }
            dragged = event.target.closest('[data-pulpit-gadget]');
            snapshot = capture();
            dragged.classList.add('is-dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', dragged.dataset.pulpitGadget);
        }, { signal });
        grid.addEventListener('dragover', event => {
            const column = event.target.closest('[data-pulpit-column]');
            if (!dragged || !column || page.dataset.pulpitSaving === 'true') return;
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
            if (!dragged || !column || page.dataset.pulpitSaving === 'true') return;
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
        document.addEventListener('ancore:before-navigate', event => { if (page.dataset.pulpitSaving === 'true') event.preventDefault(); }, { signal });
        window.addEventListener('beforeunload', event => {
            if (page.dataset.pulpitSaving === 'true') { event.preventDefault(); event.returnValue = ''; }
        }, { signal });
    }
    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
