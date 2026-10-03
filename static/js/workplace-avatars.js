(() => {
    const instances = new Set();
    function init() {
        for (const instance of instances) {
            if (!instance.form.isConnected) {
                instance.close();
                instances.delete(instance);
            }
        }
        document.querySelectorAll('[data-workplace-avatar-picker]').forEach(picker => {
            if (picker.dataset.initialized) return;
            const form = picker.closest('form');
            const editor = picker.closest('[data-profile-photo-editor]');
            const modal = picker.closest('[data-workplace-avatar-modal]');
            const preview = editor?.querySelector('[data-profile-photo-preview]');
            if (!form || !preview || !editor.profilePhotoEditorApi) return;
            picker.dataset.initialized = 'true';
            const api = editor.profilePhotoEditorApi;
            const file = picker.querySelector('[type=file]');
            const drop = picker.querySelector('[data-workplace-avatar-drop]');
            const uploadPreview = picker.querySelector('[data-workplace-avatar-upload-preview]');
            const error = picker.querySelector('[data-workplace-avatar-error]');
            const triggers = [...editor.querySelectorAll('[data-workplace-avatar-open]')];
            const radios = [...picker.querySelectorAll('input[name="avatar"]')];
            // Keep fields in their Workspace form while the dialog is above its parent.
            modal.querySelectorAll('input').forEach(input => input.setAttribute('form', form.id));
            let photoUrl = api.snapshot().url;
            let snapshot, anchor, committed = false, inertElements = [];
            const selected = () => radios.find(radio => radio.checked)?.value || 'auto';
            const select = value => { radios.find(radio => radio.value === value).checked = true; };
            const clearError = () => { error.hidden = true; error.textContent = ''; };
            const showError = message => { error.textContent = message; error.hidden = false; };
            function render() {
                const choice = selected();
                [...preview.classList].filter(name => name.startsWith('space-avatar-art')).forEach(name => preview.classList.remove(name));
                preview.replaceChildren();
                preview.classList.toggle('has-photo', choice === 'upload' && Boolean(photoUrl));
                if (choice === 'upload' && photoUrl) {
                    const image = document.createElement('img');
                    image.src = photoUrl;
                    image.alt = '';
                    preview.append(image);
                } else {
                    const art = choice === 'auto' || choice === 'upload' ? picker.dataset.automaticAvatar : `space-avatar-art--${choice}`;
                    preview.classList.add('space-avatar-art', art);
                }
                uploadPreview.replaceChildren();
                uploadPreview.hidden = !photoUrl;
                if (photoUrl) {
                    const image = document.createElement('img');
                    image.src = photoUrl;
                    image.alt = 'Podgląd własnego awatara';
                    uploadPreview.append(image);
                }
            }
            function open() {
                if (modal.classList.contains('is-open')) return;
                snapshot = { choice: selected(), photo: api.snapshot() };
                committed = false;
                clearError();
                anchor = document.createComment('Workspace avatar dialog');
                modal.before(anchor);
                document.body.append(modal);
                inertElements = [...document.body.children].filter(element => element !== modal && !element.inert);
                inertElements.forEach(element => { element.inert = true; });
                triggers.forEach(trigger => trigger.setAttribute('aria-expanded', 'true'));
                window.AncoreTaskModals.open(modal, picker.querySelector('input:checked') || radios[0]);
            }
            function close() { window.AncoreTaskModals.close(modal); }
            function save() {
                if (selected() === 'upload' && (!photoUrl || file.files.length)) {
                    showError('Wybierz obraz i zatwierdź jego kadr.');
                    return;
                }
                if (!error.hidden) return;
                committed = true;
                close();
                form.dispatchEvent(new Event('change', { bubbles: true }));
            }
            triggers.forEach(trigger => trigger.addEventListener('click', open));
            modal.addEventListener('click', event => {
                if (event.target.closest('[data-workplace-avatar-upload]')) api.change();
                if (event.target.closest('[data-workplace-avatar-save]')) save();
                if (event.target === modal || event.target.closest('[data-close-modal]')) {
                    event.stopPropagation();
                    close();
                }
            });
            modal.addEventListener('ancore:task-modal-before-close', event => {
                if (event.target !== modal || committed || !snapshot) return;
                select(snapshot.choice);
                photoUrl = snapshot.photo.url;
                api.restore(snapshot.photo);
                render();
            });
            modal.addEventListener('ancore:task-modal-closed', event => {
                if (event.target !== modal) return;
                inertElements.forEach(element => { element.inert = false; });
                inertElements = [];
                anchor?.replaceWith(modal);
                triggers.forEach(trigger => trigger.setAttribute('aria-expanded', 'false'));
            });
            // Parent Workspace dialogs have their own keyboard handlers.
            modal.addEventListener('keydown', event => {
                if (!modal.classList.contains('is-open')) return;
                if (event.key === 'Escape') {
                    event.preventDefault(); event.stopPropagation(); close();
                } else if (event.key === 'Tab') {
                    event.stopPropagation();
                    const focusable = [...modal.querySelectorAll('button, input, [tabindex]')]
                        .filter(element => !element.disabled && element.tabIndex >= 0 && element.getClientRects().length);
                    const first = focusable[0], last = focusable.at(-1);
                    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
                    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
                } else if (event.key === 'Enter' && event.target.matches('input')) {
                    event.preventDefault(); event.stopPropagation(); save();
                }
            });
            picker.addEventListener('change', event => {
                if (!event.target.matches('input[name="avatar"]')) return;
                clearError(); render();
            });
            file.addEventListener('change', event => {
                const image = file.files[0];
                if (!image) return;
                if (!['image/png', 'image/jpeg', 'image/webp'].includes(image.type) || image.size > 5 * 1024 * 1024) {
                    event.stopImmediatePropagation(); file.value = '';
                    showError('Wybierz obraz PNG, JPG lub WebP o rozmiarze do 5 MB.');
                    return;
                }
                clearError(); select('upload');
            }, true);
            drop.addEventListener('dragover', event => { event.preventDefault(); drop.classList.add('is-drag-over'); });
            drop.addEventListener('dragleave', event => { if (!drop.contains(event.relatedTarget)) drop.classList.remove('is-drag-over'); });
            drop.addEventListener('drop', event => {
                event.preventDefault(); drop.classList.remove('is-drag-over');
                if (event.dataTransfer.files.length !== 1) { showError('Wybierz jeden obraz.'); return; }
                file.files = event.dataTransfer.files;
                file.dispatchEvent(new Event('change', { bubbles: true }));
            });
            editor.addEventListener('ancore:photo-preview', () => queueMicrotask(render));
            editor.addEventListener('ancore:photo-error', () => showError('Nie udało się odczytać obrazu. Wybierz inny plik.'));
            editor.addEventListener('ancore:photo-saved', event => {
                photoUrl = event.detail.photoUrl;
                select(photoUrl ? 'upload' : 'auto');
                clearError(); render();
            });
            form.addEventListener('reset', () => queueMicrotask(render));
            instances.add({ form, close });
            render();
        });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
    document.addEventListener('ancore:content-loaded', init);
    document.addEventListener('ancore:before-navigate', () => instances.forEach(instance => instance.close()));
})();
