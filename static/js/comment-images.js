(() => {
    if (window.AncoreCommentImages) return;
    window.AncoreCommentImages = true;
    let cleanup;
    let activeForm;

    function init() {
        const form = document.getElementById('activity-comment-form');
        if (form && form === activeForm) return;
        cleanup?.();
        activeForm = form;
        const composer = document.querySelector('[data-comment-composer]');
        if (!form || !composer) return;
        const controller = new AbortController();
        const { signal } = controller;
        const input = composer.querySelector('[data-comment-files]');
        const textarea = composer.querySelector('[data-mention-input]');
        const previews = composer.querySelector('[data-comment-previews]');
        const errorBox = composer.querySelector('[data-comment-error]');
        const status = composer.querySelector('[data-comment-status]');
        const add = composer.querySelector('[data-comment-add]');
        const send = composer.querySelector('[type="submit"]');
        const maxCount = Number(composer.dataset.imageLimit);
        const maxSize = Number(composer.dataset.imageMaxSize);
        const allowedExtensions = new Set(input.accept.toLowerCase().split(','));
        const isImage = file => /\.(jpe?g|png|gif|webp)$/i.test(file.name);
        const extension = file => file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
        let pending = [];
        let busy = false;
        let dragDepth = 0;

        function error(message = '') {
            errorBox.textContent = message;
            errorBox.hidden = !message;
        }

        function clear() {
            pending.forEach(entry => { if (entry.url) URL.revokeObjectURL(entry.url); });
            pending = [];
            input.value = '';
        }

        cleanup = () => { controller.abort(); clear(); };

        function render() {
            previews.replaceChildren();
            previews.hidden = pending.length === 0;
            pending.forEach(entry => {
                const card = document.createElement('div');
                card.className = entry.url
                    ? 'tasks-comment-image tasks-comment-image--pending'
                    : 'tasks-attachment-card tasks-attachment-card--pending tasks-comment-file';
                if (entry.url) {
                    const img = document.createElement('img');
                    img.src = entry.url;
                    img.alt = entry.file.name;
                    card.append(img);
                } else {
                    const info = document.createElement('span');
                    info.className = 'tasks-attachment-info';
                    const type = window.AttachmentIcons.extensionToTypeClass(extension(entry.file));
                    info.append(window.AttachmentIcons.createIconElement(type, 'lg'));
                    const details = document.createElement('span');
                    details.className = 'tasks-attachment-details';
                    const name = document.createElement('span');
                    name.className = 'tasks-attachment-name';
                    name.textContent = entry.file.name;
                    name.title = entry.file.name;
                    const size = document.createElement('span');
                    size.className = 'tasks-attachment-size';
                    let bytes = entry.file.size;
                    let unit = 0;
                    while (bytes >= 1024 && unit < 3) { bytes /= 1024; unit += 1; }
                    size.textContent = `${bytes.toFixed(1)} ${['B', 'KB', 'MB', 'GB'][unit]}`;
                    details.append(name, size);
                    info.append(details);
                    card.append(info);
                }
                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = entry.url ? 'tasks-issue-tool tasks-comment-image-remove' : 'tasks-delete-attach-btn';
                remove.setAttribute('aria-label', `Usuń plik: ${entry.file.name}`);
                remove.title = 'Usuń plik';
                remove.innerHTML = '<i data-icon="x" aria-hidden="true"></i>';
                remove.addEventListener('click', () => {
                    if (busy) return;
                    if (entry.url) URL.revokeObjectURL(entry.url);
                    pending = pending.filter(item => item !== entry);
                    render();
                    error();
                    add.focus();
                });
                card.append(remove);
                previews.append(card);
            });
            status.textContent = pending.length ? `Pliki do wysłania: ${pending.length}.` : '';
            window.AncoreIcons?.render(previews);
        }

        function addFiles(files) {
            if (busy) return;
            const batch = Array.from(files);
            if (!batch.length) return;
            if (pending.length + batch.length > maxCount) {
                return error(`Dodaj maksymalnie ${maxCount} plików do jednej wiadomości.`);
            }
            for (const file of batch) {
                if (!allowedExtensions.has(extension(file))) {
                    return error('Ten typ załącznika nie jest dozwolony.');
                }
                if (!file.size || file.size > maxSize) {
                    return error(`Plik nie może być pusty ani większy niż ${Math.round(maxSize / 1024 / 1024)} MB.`);
                }
            }
            pending.push(...batch.map(file => ({ file, url: isImage(file) ? URL.createObjectURL(file) : null })));
            render();
            error();
        }

        add.addEventListener('click', () => input.click(), { signal });
        input.addEventListener('change', () => {
            addFiles(input.files);
            input.value = '';
        }, { signal });
        textarea.addEventListener('paste', event => {
            const files = Array.from(event.clipboardData?.items || [])
                .filter(item => item.kind === 'file')
                .map(item => item.getAsFile()).filter(Boolean);
            if (files.length) {
                event.preventDefault();
                addFiles(files);
            }
        }, { signal });
        const isFileDrag = event => Array.from(event.dataTransfer?.types || []).includes('Files');
        composer.addEventListener('dragenter', event => {
            if (!isFileDrag(event)) return;
            event.preventDefault();
            dragDepth += 1;
            composer.classList.add('is-dragging-images');
        }, { signal });
        composer.addEventListener('dragover', event => {
            if (isFileDrag(event)) event.preventDefault();
        }, { signal });
        composer.addEventListener('dragleave', event => {
            if (!isFileDrag(event)) return;
            dragDepth = Math.max(0, dragDepth - 1);
            if (!dragDepth) composer.classList.remove('is-dragging-images');
        }, { signal });
        composer.addEventListener('drop', event => {
            if (!isFileDrag(event)) return;
            event.preventDefault();
            event.stopPropagation();
            dragDepth = 0;
            composer.classList.remove('is-dragging-images');
            addFiles(event.dataTransfer.files);
        }, { signal });

        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (busy) return;
            if (!textarea.value.trim() && !pending.length) {
                error('Wpisz treść komentarza lub dodaj plik.');
                textarea.focus();
                return;
            }
            // The mention listener has already synchronized its hidden field.
            const body = new FormData(form);
            body.delete('comment_attachments');
            pending.forEach(entry => body.append('comment_attachments', entry.file));
            busy = true;
            textarea.readOnly = true;
            add.disabled = send.disabled = true;
            previews.querySelectorAll('button').forEach(button => { button.disabled = true; });
            form.setAttribute('aria-busy', 'true');
            status.textContent = 'Wysyłanie komentarza…';
            error();
            try {
                const response = await fetch(form.getAttribute('action') || window.location.href, {
                    method: 'POST', body, signal,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data.status !== 'success') {
                    throw new Error(data.message || 'Nie udało się wysłać komentarza. Spróbuj ponownie.');
                }
                const feed = composer.closest('.tasks-issue-activity').querySelector('[data-activity-feed]');
                feed.querySelector('[data-activity-empty-initial]')?.remove();
                feed.insertAdjacentHTML('afterbegin', data.activity_html);
                window.AncoreIcons?.render(feed);
                feed.dispatchEvent(new Event('ancore:comment-added'));
                feed.scrollTop = 0;
                textarea.value = '';
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                clear();
                render();
                status.textContent = 'Komentarz wysłany.';
                textarea.focus();
            } catch (failure) {
                if (failure.name !== 'AbortError') {
                    status.textContent = '';
                    error(failure.message || 'Nie udało się wysłać komentarza. Spróbuj ponownie.');
                }
            } finally {
                busy = false;
                textarea.readOnly = false;
                add.disabled = send.disabled = false;
                previews.querySelectorAll('button').forEach(button => { button.disabled = false; });
                form.removeAttribute('aria-busy');
            }
        }, { signal });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
    window.addEventListener('pagehide', () => { cleanup?.(); activeForm = null; });
    window.addEventListener('pageshow', init);
})();
