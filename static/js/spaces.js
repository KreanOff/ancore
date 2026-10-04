(function () {
    if (window.ancoreWorkLoaded) return;
    window.ancoreWorkLoaded = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        const page = document.querySelector('[data-work-page]');
        const host = document.querySelector('[data-work-modal-host]');
        if (!page || !host) return;
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
            } catch (error) { if (!signal.aborted) window.showNotification?.(error.message, 'error'); }
            finally { pending = false; }
        }
        page.addEventListener('submit', event => { const form = event.target.closest('[data-work-action]'); if (form) { event.preventDefault(); action(form.getAttribute('action'), new FormData(form)); } }, { signal });
        let dragged;
        page.addEventListener('dragstart', event => {
            dragged = event.target.closest('[data-work-card][draggable=true]');
            if (dragged && event.target.closest('a, button')) { dragged = null; return; }
            if (dragged) { event.dataTransfer.setData('text/plain', dragged.dataset.itemId); event.dataTransfer.effectAllowed = 'move'; }
        }, { signal });
        page.addEventListener('dragover', event => { const column = event.target.closest('[data-work-column]'); if (dragged && column) { event.preventDefault(); column.classList.add('is-drag-over'); } }, { signal });
        page.addEventListener('dragleave', event => { const column = event.target.closest('[data-work-column]'); if (column && !column.contains(event.relatedTarget)) column.classList.remove('is-drag-over'); }, { signal });
        page.addEventListener('drop', event => {
            const column = event.target.closest('[data-work-column]');
            if (!dragged || !column) return;
            event.preventDefault(); column.classList.remove('is-drag-over');
            const body = new FormData(page.querySelector('[data-board-csrf]'));
            body.set('action', 'status'); body.set('status', column.dataset.workColumn);
            action(dragged.dataset.actionUrl, body); dragged = null;
        }, { signal });
        page.addEventListener('dragend', () => { dragged = null; page.querySelectorAll('.is-drag-over').forEach(column => column.classList.remove('is-drag-over')); }, { signal });
        if (modal()) display(host.innerHTML);
    }
    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
