(function () {
    if (window.ancoreWorkLoaded) return;
    window.ancoreWorkLoaded = true;
    let controller, boardArrival;

    function initTaskDetail(page, signal) {
        const form = page.querySelector('#space-task-form');
        if (!form) return;
        const save = page.querySelector('[data-space-task-save]');
        const upload = page.querySelector('[data-space-task-upload]');
        const list = page.querySelector('[data-space-task-upload-list]');
        const snapshot = () => JSON.stringify([...new FormData(form)].filter(([name, value]) =>
            name !== 'csrfmiddlewaretoken' && !(value instanceof File && !value.name)
        ).map(([name, value]) => [name, value instanceof File ? [value.name, value.size, value.lastModified] : value]));
        const initial = snapshot();
        const hasErrors = Boolean(page.querySelector('.tasks-error-banner'));
        function syncSave() {
            if (!save) return;
            const dirty = hasErrors || snapshot() !== initial;
            save.disabled = !dirty;
            save.dataset.state = dirty ? 'dirty' : 'idle';
        }
        function renderFiles() {
            if (!upload || !list) return;
            list.replaceChildren();
            [...upload.files].forEach((file, index) => {
                const card = document.createElement('div');
                card.className = 'tasks-attachment-card tasks-attachment-card--pending';
                const info = document.createElement('div'); info.className = 'tasks-attachment-info';
                const extension = file.name.includes('.') ? file.name.slice(file.name.lastIndexOf('.')).toLowerCase() : '';
                info.append(window.AttachmentIcons.createIconElement(window.AttachmentIcons.extensionToTypeClass(extension), 'md'));
                const details = document.createElement('span'); details.className = 'tasks-attachment-details';
                const name = document.createElement('span');
                name.className = 'tasks-attachment-name';
                name.textContent = file.name;
                const size = document.createElement('span'); size.className = 'tasks-attachment-size';
                const unit = file.size ? Math.min(3, Math.floor(Math.log(file.size) / Math.log(1024))) : 0;
                size.textContent = `${parseFloat((file.size / 1024 ** unit).toFixed(1))} ${['B', 'KB', 'MB', 'GB'][unit]}`;
                details.append(name, size); info.append(details);
                const remove = document.createElement('button');
                remove.type = 'button'; remove.className = 'tasks-delete-attach-btn';
                remove.dataset.spaceTaskRemoveUpload = String(index);
                remove.setAttribute('aria-label', `Usuń wybrany plik ${file.name}`);
                remove.append(window.AncoreIcons.create('trash-2'));
                card.append(info, remove); list.append(card);
            });
            window.AncoreIcons.render(list);
        }
        page.addEventListener('input', syncSave, { signal });
        page.addEventListener('change', event => {
            if (event.target === upload) renderFiles();
            if (event.target.matches('.tasks-subtasks-board .tasks-row-checkbox')) event.target.closest('.tasks-issue-row').classList.toggle('checked', event.target.checked);
            syncSave();
        }, { signal });
        form.addEventListener('submit', () => {
            if (save) { save.disabled = true; save.dataset.state = 'saving'; save.textContent = 'Zapisywanie...'; }
        }, { signal });
        page.addEventListener('click', async event => {
            if (event.target.closest('[data-space-task-choose-files]')) upload?.click();
            const remove = event.target.closest('[data-space-task-remove-upload]');
            if (remove && upload) {
                const transfer = new DataTransfer();
                [...upload.files].forEach((file, index) => { if (index !== Number(remove.dataset.spaceTaskRemoveUpload)) transfer.items.add(file); });
                upload.files = transfer.files; renderFiles(); syncSave();
            }
            const copy = event.target.closest('[data-space-task-copy]');
            if (copy) {
                try {
                    await navigator.clipboard.writeText(copy.dataset.spaceTaskCopy);
                    window.showNotification?.('Skopiowano ID zadania.', 'success');
                } catch (error) { window.showNotification?.('Nie udało się skopiować ID zadania.', 'error'); }
            }
        }, { signal });
        page.addEventListener('ancore:task-history-added', event => {
            const feed = page.querySelector('[data-activity-feed="history"]');
            feed.querySelector('[data-activity-empty-initial]')?.remove();
            feed.insertAdjacentHTML('afterbegin', event.detail || '');
            window.AncoreIcons?.render(feed);
        }, { signal });
        const subtaskModal = document.getElementById('space-subtask-modal');
        let background = [];
        function openSubtask() {
            for (let node = subtaskModal; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) { sibling.inert = true; background.push(sibling); }
                });
            }
            window.AncoreTaskModals.open(subtaskModal, subtaskModal.querySelector('[name="subtask-title"]'));
        }
        function restoreBackground() { background.forEach(node => { node.inert = false; }); background = []; }
        subtaskModal?.addEventListener('ancore:task-modal-closed', restoreBackground, { signal });
        signal.addEventListener('abort', restoreBackground, { once: true });
        page.addEventListener('click', event => {
            if (event.target.closest('[data-space-subtask-open]')) openSubtask();
            const sort = event.target.closest('[data-space-subtasks-sort]');
            if (sort) {
                const descending = sort.dataset.direction !== 'desc';
                sort.dataset.direction = descending ? 'desc' : 'asc';
                page.querySelectorAll('.tasks-subtasks-board .tasks-issue-list').forEach(list => {
                    [...list.children].sort((a, b) => (descending ? -1 : 1) * a.querySelector('.tasks-row-title').textContent.trim().localeCompare(b.querySelector('.tasks-row-title').textContent.trim(), 'pl', { numeric: true })).forEach(row => list.append(row));
                });
                window.showNotification?.(descending ? 'Podzadania posortowane malejąco.' : 'Podzadania posortowane rosnąco.', 'success');
            }
            if (event.target.closest('[data-space-subtasks-delete]')) {
                const selected = [...page.querySelectorAll('.tasks-subtasks-board .tasks-row-checkbox:checked')].map(input => input.value);
                if (!selected.length) { window.showNotification?.('Zaznacz podzadania do usunięcia.', 'info'); return; }
                window.showConfirmModal({ title: 'Usuń podzadania', message: `Czy na pewno chcesz usunąć zaznaczone podzadania (${selected.length})?`, confirmText: 'Usuń', onConfirm: () => {
                    const post = document.createElement('form'); post.method = 'post';
                    const params = [['csrfmiddlewaretoken', form.elements.csrfmiddlewaretoken.value], ['action', 'delete_subtasks'], ...selected.map(id => ['subtask_ids', id])];
                    params.forEach(([name, value]) => { const input = document.createElement('input'); input.type = 'hidden'; input.name = name; input.value = value; post.append(input); });
                    document.body.append(post); post.submit();
                } });
            }
        }, { signal });
        if (subtaskModal?.classList.contains('is-open')) openSubtask();
        syncSave();
    }

    function init() {
        controller?.abort();
        if (boardArrival && boardArrival.url !== window.location.href) boardArrival = null;
        controller = new AbortController();
        const { signal } = controller;
        const page = document.querySelector('[data-work-page]');
        const host = document.querySelector('[data-work-modal-host]');
        if (!page || !host) return;
        initTaskDetail(page, signal);
        let pending = false, discard = false, initial = '', previousFocus, background = [], previewUrl;
        const modal = () => host.querySelector('[data-work-modal]');
        const values = () => JSON.stringify([...new FormData(host.querySelector('form'))].map(([key, value]) => [key, value instanceof File ? (value.name ? [value.name, value.size, value.lastModified] : null) : value]));
        const dirty = () => modal() && values() !== initial;
        const restore = () => { background.forEach(element => { element.inert = false; }); background = []; };
        const clearPreview = () => { if (previewUrl) URL.revokeObjectURL(previewUrl); previewUrl = null; };
        function inertBackground() {
            for (let node = host; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
                        sibling.inert = true; background.push(sibling);
                    }
                });
            }
        }
        async function request(url, options = {}, header = 'X-Work-Modal') {
            const response = await fetch(url, { ...options, credentials: 'same-origin', signal: AbortSignal.any([signal, AbortSignal.timeout(20000)]), headers: { [header]: 'true' } });
            if (response.redirected || (!response.ok && response.status !== 400)) throw new Error('Nie udało się zapisać zmian. Odśwież stronę i spróbuj ponownie.');
            return response.json();
        }
        async function navigate(url) {
            if (!await window.AncoreApp?.navigate(url, { replace: true })) window.location.href = url;
        }
        function configureWizard() {
            const wizard = host.querySelector('[data-space-wizard]');
            if (!wizard) return;
            const kind = wizard.querySelector('[name=kind]'), template = wizard.querySelector('[name=template]');
            const picker = wizard.querySelector('[data-space-template-picker]');
            const details = wizard.querySelector('[data-space-details]');
            const fields = wizard.querySelector('[data-space-fields]');
            const submit = wizard.querySelector('[data-space-create]');
            const cards = [...picker.querySelectorAll('[data-space-template]')];
            function showDetails(show, focus = false) {
                picker.hidden = show; details.hidden = !show;
                fields.disabled = !show; submit.hidden = !show;
                window.AncoreCustomSelect?.refresh(host);
                if (focus) {
                    wizard.querySelector('.tasks-modal__body').scrollTop = 0;
                    (show ? fields.querySelector('[name=name]') : cards.find(card => card.dataset.spaceTemplate === template.value) || cards[0])?.focus();
                }
            }
            function selectTemplate(card, focus = false) {
                template.value = card.dataset.spaceTemplate; kind.value = card.dataset.spaceKind;
                cards.forEach(option => option.setAttribute('aria-pressed', String(option === card)));
                const art = wizard.querySelector('[data-space-selected-art]');
                art.src = card.querySelector('img').src; art.hidden = false;
                wizard.querySelector('[data-space-selected-label]').textContent = card.querySelector('[data-space-template-label]').textContent;
                wizard.querySelector('[data-space-selected-kind]').textContent = card.querySelector('.work-caption').textContent;
                showDetails(true, focus);
            }
            const selected = cards.find(card => card.dataset.spaceTemplate === template.value);
            if (selected) selectTemplate(selected);
            else showDetails(false);
            picker.addEventListener('click', event => {
                const card = event.target.closest('[data-space-template]');
                if (card && !pending) selectTemplate(card, true);
            }, { signal });
            wizard.querySelector('[data-space-change-template]').addEventListener('click', () => {
                if (!pending) showDetails(false, true);
            }, { signal });
            const management = host.querySelector('[name=management]'), config = host.querySelector('[name=configuration]');
            const sync = () => { if (management && config) { config.disabled = management.value !== 'company'; if (config.disabled) config.value = ''; window.AncoreCustomSelect?.refresh(host); } };
            management?.addEventListener('change', sync, { signal }); sync();
        }
        function configureAvatarPicker() {
            const picker = host.querySelector('[data-space-avatar-picker]');
            if (!picker) return;
            const file = picker.querySelector('[data-space-avatar-file]');
            const preview = picker.querySelector('[data-space-avatar-preview]');
            const filename = picker.querySelector('[data-space-avatar-filename]');
            const error = picker.querySelector('[data-space-avatar-upload-error]');
            const drop = picker.querySelector('[data-space-avatar-drop]');
            file.setAttribute('aria-describedby', 'space-avatar-upload-help');
            function updateFile() {
                const selected = file.files[0];
                if (!selected) return;
                error.hidden = true;
                if (selected.size > 5 * 1024 * 1024 || !/\.(png|jpe?g|webp)$/i.test(selected.name)) {
                    error.textContent = 'Wybierz obraz PNG, JPG lub WebP o rozmiarze do 5 MB.';
                    error.hidden = false; file.value = ''; return;
                }
                clearPreview();
                previewUrl = URL.createObjectURL(selected);
                const img = document.createElement('img');
                img.src = previewUrl; img.alt = 'Podgląd własnego awatara';
                preview.replaceChildren(img); preview.hidden = false;
                filename.textContent = selected.name;
                picker.querySelector('[name=avatar][value=upload]').checked = true;
            }
            file.addEventListener('change', updateFile, { signal });
            picker.addEventListener('change', event => {
                if (event.target.name === 'avatar' && event.target.value !== 'upload') {
                    file.value = ''; filename.textContent = ''; error.hidden = true;
                    // Keep a saved photo available until the new selection is saved.
                    clearPreview();
                    const savedPreview = picker.dataset.savedPreview;
                    if (savedPreview) { preview.querySelector('img').src = savedPreview; preview.hidden = false; }
                    else { preview.replaceChildren(); preview.hidden = true; }
                }
            }, { signal });
            picker.dataset.savedPreview = preview.querySelector('img')?.getAttribute('src') || '';
            drop.addEventListener('dragover', event => { event.preventDefault(); if (!pending) drop.classList.add('is-drag-over'); }, { signal });
            drop.addEventListener('dragleave', event => { if (!drop.contains(event.relatedTarget)) drop.classList.remove('is-drag-over'); }, { signal });
            drop.addEventListener('drop', event => {
                event.preventDefault(); drop.classList.remove('is-drag-over');
                if (pending) return;
                if (event.dataTransfer.files.length !== 1) {
                    error.textContent = 'Wybierz jeden obraz.'; error.hidden = false; return;
                }
                file.files = event.dataTransfer.files; updateFile();
            }, { signal });
            updateFile();
        }
        function display(html, preserve = false) {
            const oldFile = preserve ? host.querySelector('[data-space-avatar-file]') : null;
            clearPreview();
            restore(); host.innerHTML = html;
            if (!modal()) throw new Error('Brak formularza.');
            const newFile = host.querySelector('[data-space-avatar-file]');
            if (oldFile?.files.length && newFile) newFile.files = oldFile.files;
            configureWizard();
            configureAvatarPicker();
            if (!preserve) initial = values();
            window.AncoreIcons?.render(host);
            const focusTarget = host.querySelector('[aria-invalid=true]:not([type=hidden]):not(:disabled)')
                || host.querySelector('input:checked:not(:disabled)')
                || host.querySelector('input:not([type=hidden]):not(:disabled)')
                || host.querySelector('[data-space-template][aria-pressed=true]')
                || host.querySelector('[data-space-template]');
            window.AncoreTaskModals.open(modal(), focusTarget);
            inertBackground();
        }
        document.addEventListener('click', async event => {
            const trigger = event.target.closest('[data-work-open]');
            if (!trigger || (!page.contains(trigger) && !trigger.closest('.sidebar, [data-sidebar-collapsed-flyout]')) || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            if (pending || modal()) return;
            pending = true;
            previousFocus = trigger.closest('[data-sidebar-collapsed-flyout]')
                ? document.querySelector('[data-sidebar-group="spaces"] [data-sidebar-group-toggle]')
                : trigger.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || trigger;
            trigger.setAttribute('aria-busy', 'true');
            try { const result = await request(trigger.href); if (!signal.aborted) display(result.html); }
            catch (error) { if (!signal.aborted) window.showNotification?.(error.message, 'error'); }
            finally { pending = false; trigger.removeAttribute('aria-busy'); }
        }, { signal, capture: true });
        host.addEventListener('submit', async event => {
            const form = event.target.closest('[data-work-form]');
            if (!form) return;
            event.preventDefault(); if (pending) return;
            if (form.querySelector('[data-space-template-picker]:not([hidden])')) return;
            const body = new FormData(form), buttons = [...form.querySelectorAll('button')];
            pending = true; buttons.forEach(button => { button.disabled = true; });
            const errorBox = form.querySelector('[data-work-error]'); errorBox.hidden = true;
            try {
                const result = await request(form.getAttribute('action'), { method: 'POST', body });
                if (signal.aborted) return;
                if (result.saved) { pending = false; discard = true; window.AncoreTaskModals.close(modal()); await navigate(result.url); }
                else display(result.html, true);
            } catch (error) { if (!signal.aborted) { errorBox.textContent = error.message; errorBox.hidden = false; } }
            finally { pending = false; buttons.forEach(button => { button.disabled = false; }); }
        }, { signal });
        host.addEventListener('ancore:task-modal-before-close', event => {
            if (pending) { event.preventDefault(); return; }
            if (discard || !dirty()) return;
            event.preventDefault();
            window.showConfirmModal({ title: 'Niezapisane zmiany', message: 'Zamknąć okno bez zapisania zmian?', confirmText: 'Zamknij bez zapisu', cancelText: 'Wróć do edycji', onConfirm: () => { if (!signal.aborted) { discard = true; window.AncoreTaskModals.close(modal()); } } });
        }, { signal });
        host.addEventListener('ancore:task-modal-closed', () => {
            clearPreview(); restore(); host.replaceChildren(); discard = false;
            previousFocus?.focus({ preventScroll: true });
            const directory = host.dataset.workDirectoryUrl;
            if (directory) window.history.replaceState(window.history.state, '', directory);
        }, { signal });
        document.addEventListener('ancore:before-navigate', event => { if (modal() && (pending || dirty())) { event.preventDefault(); window.AncoreTaskModals.close(modal()); } }, { signal });
        window.addEventListener('beforeunload', event => { if (dirty()) { event.preventDefault(); event.returnValue = ''; } }, { signal });
        signal.addEventListener('abort', restore, { once: true });
        signal.addEventListener('abort', clearPreview, { once: true });

        async function action(url, body) {
            if (pending) return;
            pending = true;
            try {
                const result = await request(url, { method: 'POST', body }, 'X-Work-Action');
                if (result.error) throw new Error(result.error);
                if (!signal.aborted) await navigate(window.location.href);
                return true;
            } catch (error) {
                if (!signal.aborted) window.showNotification?.(
                    ['TypeError', 'TimeoutError'].includes(error.name) ? 'Nie udało się zapisać zmian. Spróbuj ponownie.' : error.message, 'error');
            } finally { pending = false; }
            return false;
        }
        page.addEventListener('submit', event => { const form = event.target.closest('[data-work-action]'); if (form) { event.preventDefault(); action(form.getAttribute('action'), new FormData(form)); } }, { signal });
        const board = page.querySelector('[data-work-board]');
        const arrival = boardArrival;
        boardArrival = null;
        if (board) {
            let dragged, dragPreview, dropPosition, pointerPoint, scrollFrame, scrollTime, startedOnControl = false;
            const marker = document.createElement('span');
            marker.className = 'work-board-drop-marker';
            marker.setAttribute('aria-hidden', 'true');
            const status = message => { const live = document.querySelector('[data-work-page] [data-board-status]'); if (live) live.textContent = message; };
            const controls = 'button, input, select, textarea, [data-row-actions]';
            board.querySelectorAll('[data-work-card] a, [data-work-card] img').forEach(element => { element.draggable = false; });
            if (arrival?.url === window.location.href) {
                const card = [...board.querySelectorAll('[data-work-card]')].find(element =>
                    element.dataset.itemId === arrival.itemId && element.closest('[data-work-column]').dataset.workColumn === arrival.column);
                if (card) {
                    card.classList.add('is-board-arriving');
                    card.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
                    const timer = window.setTimeout(() => card.classList.remove('is-board-arriving'), 600);
                    signal.addEventListener('abort', () => { window.clearTimeout(timer); card.classList.remove('is-board-arriving'); }, { once: true });
                }
            }
            function moveBoardDragPreview(event) {
                if (!dragPreview || (!event.clientX && !event.clientY)) return;
                const { element, offsetX, offsetY, scale, width, height } = dragPreview;
                const left = Math.max(8, Math.min(event.clientX - offsetX, window.innerWidth - width - 8));
                const top = Math.max(8, Math.min(event.clientY - offsetY, window.innerHeight - height - 8));
                element.style.transform = `translate3d(${left / scale}px, ${top / scale}px, 0)`;
            }
            function createBoardDragPreview(card, event) {
                const bounds = card.getBoundingClientRect(), style = window.getComputedStyle(card);
                const element = card.cloneNode(true), image = document.createElement('canvas');
                element.classList.remove('is-dragging', 'is-board-arriving');
                element.classList.add('work-board-drag-preview');
                element.removeAttribute('draggable');
                element.removeAttribute('data-work-card');
                element.removeAttribute('data-item-id');
                element.removeAttribute('data-action-url');
                element.querySelectorAll('[data-row-actions-panel]').forEach(panel => panel.remove());
                [element, ...element.querySelectorAll('*')].forEach(node => {
                    ['id', 'for', 'aria-controls', 'aria-labelledby', 'popovertarget', 'data-row-actions', 'data-row-actions-toggle', 'data-work-open', 'data-work-action'].forEach(attribute => node.removeAttribute(attribute));
                });
                element.inert = true;
                element.setAttribute('aria-hidden', 'true');
                element.style.width = `${card.offsetWidth}px`;
                element.style.minHeight = `${card.offsetHeight}px`;
                element.style.font = style.font;
                element.style.color = style.color;
                element.style.setProperty('--tasks-kanban-header-radius', style.getPropertyValue('--tasks-kanban-header-radius') || '5px');
                image.width = image.height = 1;
                image.className = 'work-board-native-drag-image';
                image.setAttribute('aria-hidden', 'true');
                const scale = bounds.width / card.offsetWidth || 1;
                dragPreview = { element, image, scale, width: bounds.width, height: bounds.height, offsetX: event.clientX - bounds.left, offsetY: event.clientY - bounds.top };
                element.style.transformOrigin = `${dragPreview.offsetX / scale}px ${dragPreview.offsetY / scale}px`;
                moveBoardDragPreview(event);
                document.body.append(element, image);
                event.dataTransfer.setDragImage(image, 0, 0);
            }
            function clearBoardDrop() {
                board.querySelectorAll('.is-drag-over').forEach(column => column.classList.remove('is-drag-over'));
                marker.remove();
                dropPosition = null;
            }
            function positionBoardDrop(column, y) {
                if (!column || !board.contains(column) || !dragged || pending) { clearBoardDrop(); return; }
                board.querySelectorAll('.is-drag-over').forEach(target => { if (target !== column) target.classList.remove('is-drag-over'); });
                const list = column.querySelector('.tasks-kanban-column__list');
                const cards = [...list.querySelectorAll('[data-work-card]')].filter(card => card !== dragged);
                const collapsed = column.classList.contains('is-collapsed');
                const index = collapsed ? -1 : cards.findIndex(card => { const rect = card.getBoundingClientRect(); return y < rect.top + rect.height / 2; });
                const insertion = index < 0 ? cards.length : index;
                const before = cards[insertion] || null, after = cards[insertion - 1] || null;
                dropPosition = { column, before, after };
                column.classList.add('is-drag-over');
                const bounds = column.getBoundingClientRect(), listBounds = list.getBoundingClientRect();
                const scale = bounds.width / column.offsetWidth || 1;
                const gap = (parseFloat(getComputedStyle(list).rowGap) || 8) * scale;
                const header = column.querySelector('header').getBoundingClientRect();
                const top = collapsed ? header.bottom + gap / 2 : before ? before.getBoundingClientRect().top - gap / 2 : after ? after.getBoundingClientRect().bottom + gap / 2 : listBounds.top + gap / 2;
                const minimum = collapsed ? header.bottom : listBounds.top;
                const maximum = collapsed ? bounds.bottom : listBounds.bottom;
                marker.style.top = `${(Math.max(minimum + 2, Math.min(top, maximum - 2)) - bounds.top) / scale}px`;
                if (marker.parentNode !== column) column.append(marker);
            }
            function edgeSpeed(point, start, end) {
                const edge = Math.min(48, (end - start) / 4);
                if (point < start || point > end) return 0;
                return point < start + edge ? -600 * (start + edge - point) / edge : point > end - edge ? 600 * (point - end + edge) / edge : 0;
            }
            function scrollBoard(time) {
                if (!dragged) return;
                const elapsed = Math.min(time - (scrollTime || time), 32) / 1000;
                scrollTime = time;
                if (pointerPoint) {
                    const bounds = board.getBoundingClientRect();
                    if (pointerPoint.y >= bounds.top && pointerPoint.y <= bounds.bottom) board.scrollLeft += edgeSpeed(pointerPoint.x, Math.max(0, bounds.left), Math.min(innerWidth, bounds.right)) * elapsed;
                    const column = document.elementFromPoint(pointerPoint.x, pointerPoint.y)?.closest('[data-work-column]');
                    if (column && board.contains(column)) {
                        const list = column.querySelector('.tasks-kanban-column__list'), rect = list.getBoundingClientRect();
                        if (!column.classList.contains('is-collapsed')) list.scrollTop += edgeSpeed(pointerPoint.y, rect.top, rect.bottom) * elapsed;
                        positionBoardDrop(column, pointerPoint.y);
                    } else clearBoardDrop();
                }
                scrollFrame = requestAnimationFrame(scrollBoard);
            }
            function resetBoardDrag() {
                dragged?.classList.remove('is-dragging');
                dragged = null;
                dragPreview?.element.remove();
                dragPreview?.image.remove();
                dragPreview = null;
                pointerPoint = null;
                cancelAnimationFrame(scrollFrame);
                scrollFrame = scrollTime = null;
                startedOnControl = false;
                board.classList.remove('is-board-dragging');
                clearBoardDrop();
            }
            board.addEventListener('pointerdown', event => {
                startedOnControl = Boolean(event.target.closest(controls));
            }, { signal });
            board.addEventListener('dragstart', event => {
                const card = event.target.closest('[data-work-card][draggable=true]');
                if (!card) return;
                if (pending || startedOnControl || event.target.closest(controls)) { event.preventDefault(); return; }
                dragged = card;
                event.dataTransfer.clearData();
                event.dataTransfer.setData('text/plain', card.dataset.itemId);
                event.dataTransfer.effectAllowed = 'move';
                createBoardDragPreview(card, event);
                board.classList.add('is-board-dragging');
                card.classList.add('is-dragging');
                status('Przeciągnij zadanie na wybraną pozycję. Przerywana linia wskazuje miejsce wstawienia. Escape anuluje.');
                scrollFrame = requestAnimationFrame(scrollBoard);
            }, { signal });
            document.addEventListener('dragover', event => {
                moveBoardDragPreview(event);
                if (dragged) pointerPoint = { x: event.clientX, y: event.clientY };
            }, { signal });
            board.addEventListener('dragenter', event => {
                if (dragged && !pending && event.target.closest('[data-work-column]')) {
                    event.preventDefault();
                    event.dataTransfer.dropEffect = 'move';
                }
            }, { signal });
            board.addEventListener('dragover', event => {
                if (!dragged || pending) return;
                const column = event.target.closest('[data-work-column]');
                positionBoardDrop(column, event.clientY);
                if (dropPosition) { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; }
            }, { signal });
            board.addEventListener('dragleave', event => {
                const column = event.target.closest('[data-work-column]');
                if (column && !column.contains(event.relatedTarget) && dropPosition?.column === column) clearBoardDrop();
            }, { signal });
            board.addEventListener('drop', async event => {
                const column = event.target.closest('[data-work-column]');
                if (!dragged || !column) return;
                event.preventDefault();
                positionBoardDrop(column, event.clientY);
                if (!dropPosition || pending) { resetBoardDrag(); return; }
                const card = dragged, position = dropPosition, source = card.closest('[data-work-column]');
                const original = [...source.querySelectorAll('[data-work-card]')];
                const index = original.indexOf(card);
                if (source === column && (original[index + 1] || null) === position.before && (original[index - 1] || null) === position.after) { resetBoardDrag(); return; }
                const body = new FormData(page.querySelector('[data-board-csrf]'));
                body.set('action', 'position'); body.set('status', column.dataset.workColumn); body.set('return_view', 'board');
                body.set('space', board.dataset.spaceId);
                body.set('source_status', card.dataset.status); body.set('source_sprint', card.dataset.sprintId); body.set('source_rank', card.dataset.rank);
                body.set('before', position.before?.dataset.itemId || ''); body.set('after', position.after?.dataset.itemId || '');
                body.set('before_rank', position.before?.dataset.rank || ''); body.set('after_rank', position.after?.dataset.rank || '');
                resetBoardDrag();
                board.setAttribute('aria-busy', 'true');
                status('Zapisuję położenie zadania.');
                const nextArrival = { itemId: card.dataset.itemId, column: column.dataset.workColumn, url: window.location.href };
                boardArrival = nextArrival;
                const saved = await action(card.dataset.actionUrl, body);
                if (!signal.aborted) board.removeAttribute('aria-busy');
                status(saved ? 'Zapisano położenie zadania.' : 'Nie zapisano położenia zadania. Spróbuj ponownie.');
                if (!saved && boardArrival === nextArrival) boardArrival = null;
            }, { signal });
            board.addEventListener('dragend', resetBoardDrag, { signal });
            document.addEventListener('keydown', event => { if (event.key === 'Escape' && dragged) { resetBoardDrag(); status('Anulowano przeciąganie zadania.'); } }, { signal });
            signal.addEventListener('abort', resetBoardDrag, { once: true });
        }
        const backlog = page.querySelector('[data-work-backlog]');
        if (backlog) {
            const bulk = page.querySelector('[data-backlog-bulk]');
            const boxes = () => [...backlog.querySelectorAll('[data-work-backlog-row] > .tasks-row-checkbox:not(:disabled)')];
            const selected = () => boxes().filter(box => box.checked);
            function syncSelection() {
                const checked = selected();
                if (bulk) {
                    const wasHidden = bulk.hidden;
                    bulk.hidden = !checked.length;
                    bulk.querySelector('[data-backlog-selection-count]').textContent = checked.length ? `Zaznaczono: ${checked.length}` : '';
                    if (wasHidden && checked.length) window.AncoreCustomSelect?.refresh(bulk);
                }
            }
            backlog.addEventListener('change', syncSelection, { signal });
            bulk?.querySelector('[data-backlog-clear-selection]').addEventListener('click', () => {
                const focus = selected()[0] || boxes()[0];
                boxes().forEach(box => { box.checked = false; });
                syncSelection(); focus?.focus();
            }, { signal });
            bulk?.addEventListener('submit', async event => {
                event.preventDefault();
                if (pending || !selected().length) return;
                const body = new FormData(bulk), positions = {};
                selected().forEach(box => {
                    const row = box.closest('[data-work-backlog-row]');
                    body.append('item_ids', row.dataset.itemId);
                    positions[row.dataset.itemId] = [row.dataset.sprintId ? Number(row.dataset.sprintId) : null, Number(row.dataset.rank)];
                });
                body.set('positions', JSON.stringify(positions));
                bulk.setAttribute('aria-busy', 'true');
                const saved = await action(bulk.getAttribute('action'), body);
                if (!signal.aborted) bulk.removeAttribute('aria-busy');
                if (saved) window.showNotification?.('Zapisano planowanie zaznaczonych zadań.', 'success');
            }, { signal });
            syncSelection();
            let draggedRow, dropPosition, pointer, scrollFrame, pointerPoint;
            const content = backlog.closest('.work-content');
            const status = message => {
                const live = document.querySelector('[data-backlog-status]');
                if (live) live.textContent = message;
            };
            function clearIndicators() {
                backlog.querySelectorAll('.is-backlog-drop-target, .is-backlog-drop-before, .is-backlog-drop-after').forEach(element => {
                    element.classList.remove('is-backlog-drop-target', 'is-backlog-drop-before', 'is-backlog-drop-after');
                });
                dropPosition = null;
            }
            function resetDrag() {
                draggedRow?.classList.remove('is-dragging');
                draggedRow = null;
                clearIndicators();
                cancelAnimationFrame(scrollFrame);
                scrollFrame = null;
            }
            function positionAt(target, y) {
                const group = target?.closest('[data-work-backlog-group]');
                clearIndicators();
                if (!group || !backlog.contains(group) || !draggedRow || pending) return;
                const rows = [...group.querySelectorAll('[data-work-backlog-row]')].filter(row => row !== draggedRow);
                // A collapsed section accepts a move to the end of its visible group.
                const index = group.classList.contains('is-collapsed') ? rows.length : rows.findIndex(row => {
                    const rect = row.getBoundingClientRect();
                    return y < rect.top + rect.height / 2;
                });
                const insertion = index === -1 ? rows.length : index;
                const before = rows[insertion] || null, after = rows[insertion - 1] || null;
                group.classList.add('is-backlog-drop-target');
                if (before) before.classList.add('is-backlog-drop-before');
                else if (after) after.classList.add('is-backlog-drop-after');
                dropPosition = { group, before, after };
            }
            async function commitDrop() {
                if (!draggedRow || !dropPosition || pending) { resetDrag(); return; }
                const row = draggedRow, position = dropPosition;
                const body = new FormData(backlog.querySelector('[data-backlog-csrf]'));
                body.set('action', 'plan'); body.set('return_view', 'backlog');
                body.set('space', backlog.dataset.spaceId);
                body.set('source_sprint', row.dataset.sprintId); body.set('source_rank', row.dataset.rank);
                body.set('sprint', position.group.dataset.sprintId);
                body.set('before', position.before?.dataset.itemId || '');
                body.set('after', position.after?.dataset.itemId || '');
                const label = position.group.dataset.groupLabel;
                resetDrag();
                backlog.setAttribute('aria-busy', 'true');
                status('Zapisuję położenie zadania.');
                const saved = await action(row.dataset.actionUrl, body);
                if (!signal.aborted) backlog.removeAttribute('aria-busy');
                status(saved ? `Zapisano położenie zadania. ${label}.` : 'Nie zapisano położenia zadania. Spróbuj ponownie.');
            }
            backlog.addEventListener('dragstart', event => {
                const row = event.target.closest('[data-work-backlog-row][draggable=true]');
                if (!row) return;
                if (pending || event.target.closest('a, button, input, select, textarea')) { event.preventDefault(); return; }
                draggedRow = row;
                row.classList.add('is-dragging');
                event.dataTransfer.effectAllowed = 'move';
                event.dataTransfer.setData('application/x-ancore-backlog', row.dataset.itemId);
                event.dataTransfer.setData('text/plain', row.dataset.itemId);
                status('Przeciągnij zadanie na inną pozycję lub do wybranej sekcji. Escape anuluje.');
            }, { signal });
            backlog.addEventListener('dragover', event => {
                if (!draggedRow || pending) return;
                positionAt(event.target, event.clientY);
                if (dropPosition) { event.preventDefault(); event.dataTransfer.dropEffect = 'move'; }
            }, { signal });
            backlog.addEventListener('dragleave', event => {
                if (!backlog.contains(event.relatedTarget)) clearIndicators();
            }, { signal });
            backlog.addEventListener('drop', event => {
                if (!draggedRow) return;
                event.preventDefault();
                positionAt(event.target, event.clientY);
                commitDrop();
            }, { signal });
            backlog.addEventListener('dragend', resetDrag, { signal });
            // Touch starts on the existing priority icon; ordinary swipes still scroll.
            backlog.addEventListener('pointerdown', event => {
                const handle = event.target.closest('[data-work-backlog-row][draggable=true] > .tasks-row-priority');
                if (!handle || event.pointerType === 'mouse' || !event.isPrimary || pending) return;
                event.preventDefault();
                pointer = { id: event.pointerId, handle, row: handle.closest('[data-work-backlog-row]'), x: event.clientX, y: event.clientY };
                handle.setPointerCapture(event.pointerId);
            }, { signal });
            function scrollTouch() {
                if (!pointer || !draggedRow || !pointerPoint) { scrollFrame = null; return; }
                const rect = content.getBoundingClientRect();
                const step = pointerPoint.y < rect.top + 40 ? -10 : pointerPoint.y > rect.bottom - 40 ? 10 : 0;
                if (step) content.scrollTop += step;
                positionAt(document.elementFromPoint(pointerPoint.x, pointerPoint.y), pointerPoint.y);
                scrollFrame = requestAnimationFrame(scrollTouch);
            }
            backlog.addEventListener('pointermove', event => {
                if (!pointer || event.pointerId !== pointer.id) return;
                if (!draggedRow && Math.hypot(event.clientX - pointer.x, event.clientY - pointer.y) < 6) return;
                event.preventDefault();
                draggedRow = pointer.row;
                draggedRow.classList.add('is-dragging');
                pointerPoint = { x: event.clientX, y: event.clientY };
                positionAt(document.elementFromPoint(event.clientX, event.clientY), event.clientY);
                if (!scrollFrame) scrollFrame = requestAnimationFrame(scrollTouch);
            }, { signal });
            function releasePointer() {
                if (pointer?.handle.hasPointerCapture(pointer.id)) pointer.handle.releasePointerCapture(pointer.id);
                pointer = null;
                pointerPoint = null;
            }
            backlog.addEventListener('pointerup', event => {
                if (!pointer || event.pointerId !== pointer.id) return;
                releasePointer();
                commitDrop();
            }, { signal });
            backlog.addEventListener('pointercancel', event => {
                if (!pointer || event.pointerId !== pointer.id) return;
                releasePointer(); resetDrag();
            }, { signal });
            document.addEventListener('keydown', event => {
                if (event.key === 'Escape' && draggedRow) {
                    releasePointer(); resetDrag(); status('Anulowano przeciąganie zadania.');
                }
            }, { signal });
            signal.addEventListener('abort', () => { releasePointer(); resetDrag(); }, { once: true });
        }
        if (modal()) display(host.innerHTML);
    }
    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
