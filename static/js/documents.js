(function () {
    let controller;

    function initDocuments() {
        controller?.abort();
        controller = new AbortController();
        const options = { signal: controller.signal };
        initDocumentSidebar(options);
        initDocumentColors(options);
        const modals = initDocumentModals(options);
        initDocumentDragDrop(options, modals);
        const menu = document.querySelector('[data-documents-columns]');
        if (!menu) return;
        const storageKey = `ancore:documents:${menu.dataset.documentsColumns}:columns:v1`;
        const availableColumns = Array.from(menu.querySelectorAll('[data-document-column-toggle]'), input => input.dataset.documentColumnToggle);
        let hidden = [];
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey) || '[]');
            if (Array.isArray(saved)) hidden = saved.filter(value => availableColumns.includes(value));
        } catch (_) { /* Default columns remain visible if storage is unavailable. */ }

        function apply() {
            document.querySelectorAll('[data-document-column]').forEach(cell => {
                cell.hidden = hidden.includes(cell.dataset.documentColumn);
            });
            menu.querySelectorAll('[data-document-column-toggle]').forEach(input => {
                input.checked = !hidden.includes(input.dataset.documentColumnToggle);
            });
        }

        function save() {
            try { localStorage.setItem(storageKey, JSON.stringify(hidden)); } catch (_) {}
            apply();
        }

        menu.addEventListener('change', event => {
            const column = event.target.dataset.documentColumnToggle;
            if (!column) return;
            hidden = hidden.filter(value => value !== column);
            if (!event.target.checked) hidden.push(column);
            save();
        }, options);
        menu.querySelector('[data-document-columns-reset]').addEventListener('click', () => {
            hidden = [];
            save();
        }, options);
        document.addEventListener('click', event => {
            if (!menu.contains(event.target)) menu.open = false;
        }, { ...options, capture: true });
        menu.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                menu.open = false;
                menu.querySelector('summary').focus();
            }
        }, options);
        apply();
    }

    function initDocumentColors(options) {
        function update(input) {
            const picker = input.closest('[data-document-color-picker]');
            const icon = picker?.querySelector('[data-document-color-preview] svg');
            if (!icon || !/^#[0-9a-f]{6}$/i.test(input.value)) return;
            icon.style.setProperty('--documents-icon-color', input.value);
            if (icon.classList.contains('documents-folder-icon')) {
                icon.style.setProperty('--documents-folder-tab', input.value.toLowerCase() === picker.dataset.defaultColor
                    ? '#ffb41f' : `color-mix(in srgb, ${input.value} 82%, #000)`);
            }
        }
        document.addEventListener('input', event => {
            if (event.target.matches('[data-document-color-input]')) update(event.target);
        }, options);
        document.addEventListener('click', event => {
            const reset = event.target.closest('[data-document-color-reset]');
            if (!reset) return;
            const picker = reset.closest('[data-document-color-picker]');
            const input = picker.querySelector('[data-document-color-input]');
            input.value = picker.dataset.defaultColor;
            update(input);
        }, options);
    }

    function initDocumentModals(options) {
        const host = document.querySelector('[data-document-modal-host]');
        if (!host) return;
        let modal = host.querySelector('[data-document-dialog]');
        let directLink = Boolean(modal);
        let previousFocus;
        let pending = false;
        let closing = false;
        let inertElements = [];

        function renderUploadFiles() {
            const input = modal?.querySelector('[data-document-upload-form] input[type="file"]');
            const list = modal?.querySelector('[data-document-upload-files]');
            if (!input || !list) return;
            const units = ['B', 'KB', 'MB', 'GB', 'TB'];
            const items = Array.from(input.files, file => {
                const item = document.createElement('li');
                item.className = 'file-item';
                const details = document.createElement('div');
                details.className = 'file-details';
                const name = document.createElement('div');
                name.className = 'file-name';
                name.textContent = file.name;
                const size = document.createElement('div');
                size.className = 'file-size';
                const unit = file.size ? Math.min(Math.floor(Math.log(file.size) / Math.log(1024)), units.length - 1) : 0;
                size.textContent = `${(file.size / (1024 ** unit)).toLocaleString('pl-PL', { maximumFractionDigits: 1 })} ${units[unit]}`;
                details.append(name, size);
                item.append(details);
                return item;
            });
            list.replaceChildren(...items);
            list.hidden = !items.length;
        }

        host.addEventListener('change', event => {
            if (event.target.matches('[data-document-upload-form] input[type="file"]')) renderUploadFiles();
        }, options);

        function restoreBackground() {
            inertElements.forEach(element => { element.inert = false; });
            inertElements = [];
            if (!document.querySelector('.tasks-modal.is-open')) document.body.classList.remove('modal-open');
        }

        function activate() {
            document.body.classList.add('modal-open');
            // Keep the dialog reachable while excluding the rest of the app from keyboard navigation.
            for (let node = host; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
                        sibling.inert = true;
                        inertElements.push(sibling);
                    }
                });
            }
            window.AncoreIcons?.render(modal);
            window.AncoreCustomSelect?.refresh(modal);
            renderUploadFiles();
            const media = modal.querySelector('[data-document-preview-media]');
            if (media) {
                const finish = success => {
                    media.parentElement?.querySelector('[data-document-preview-loading]')?.setAttribute('hidden', '');
                    media.hidden = !success;
                    const error = media.parentElement?.querySelector('[data-document-preview-error]');
                    if (error) error.hidden = success;
                };
                media.addEventListener('load', () => finish(true), { ...options, once: true });
                media.addEventListener('error', () => finish(false), { ...options, once: true });
                if (media.complete) finish(media.naturalWidth > 0);
            }
            const focusTarget = modal.querySelector('[aria-invalid="true"]')
                || modal.querySelector('[data-office-create] [autofocus]')
                || modal.querySelector('input:not([type="hidden"]):not([type="file"]), textarea, select');
            (focusTarget || modal.querySelector('[data-document-modal-close]'))?.focus();
        }

        function navigate(url) {
            if (window.AncoreApp?.canNavigatePartially?.(url)) window.AncoreApp.navigate(url);
            else window.location.assign(url);
        }

        async function close() {
            if (!modal || pending || closing) return;
            closing = true;
            const returnUrl = modal.dataset.returnUrl;
            if (modal.classList.contains('app-modal-panel')) {
                modal.classList.remove('is-open');
                modal.setAttribute('aria-hidden', 'true');
                const panel = modal.querySelector('.tasks-modal__dialog');
                // getAnimations flushes the closing styles. Wait only for the
                // shell, never for controls with potentially looping animations.
                const animations = [...modal.getAnimations(), ...(panel?.getAnimations() || [])];
                await Promise.allSettled(animations.map(animation => animation.finished));
                if (options.signal.aborted) return;
            }
            modal.remove();
            modal = null;
            closing = false;
            restoreBackground();
            if (directLink) navigate(returnUrl);
            else {
                const returnFocus = previousFocus?.closest('[data-document-actions]')?.querySelector('[data-document-actions-toggle]')
                    || previousFocus?.closest('[data-section-actions]')?.querySelector('[data-section-menu-toggle]')
                    || (previousFocus?.closest('[inert]') ? document.querySelector('[data-documents-sidebar-toggle]') : previousFocus);
                if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
            }
        }

        function replaceDialog(html) {
            const parsed = new DOMParser().parseFromString(html, 'text/html');
            const next = parsed.querySelector('[data-document-dialog]');
            if (!next) throw new Error('Missing document dialog');
            // A validation error must not discard files already selected by the user.
            const files = modal?.querySelector('input[type="file"]');
            const nextFiles = next.querySelector('input[type="file"]');
            if (files && nextFiles) {
                for (const attribute of ['aria-invalid', 'aria-describedby']) {
                    if (nextFiles.hasAttribute(attribute)) files.setAttribute(attribute, nextFiles.getAttribute(attribute));
                    else files.removeAttribute(attribute);
                }
                nextFiles.replaceWith(files);
            }
            host.replaceChildren(next);
            modal = next;
            activate();
        }

        function setUploadFiles(files) {
            const input = modal?.querySelector('[data-document-upload-form] input[type="file"]');
            if (!input || pending || closing) return;
            const transfer = new DataTransfer();
            files.forEach(file => transfer.items.add(file));
            input.files = transfer.files;
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }

        async function openDialog(url, trigger, files) {
            if (pending || closing || (modal && !modal.contains(trigger))) return;
            if (!modal) previousFocus = trigger;
            pending = true;
            trigger?.setAttribute('aria-busy', 'true');
            document.querySelector('.documents-page.is-sidebar-open [data-documents-sidebar-close]')?.click();
            const menu = trigger?.closest('[data-section-actions]');
            if (menu?.querySelector('[data-section-menu-toggle]')?.getAttribute('aria-expanded') === 'true') {
                menu.querySelector('[data-section-menu-toggle]').click();
            }
            try {
                const response = await fetch(url, { headers: { 'X-Document-Modal': 'true' }, signal: options.signal });
                if (!response.ok || response.redirected) throw new Error('Unable to load dialog');
                const html = await response.text();
                if (!options.signal.aborted) replaceDialog(html);
            } catch (error) {
                if (!options.signal.aborted) {
                    if (files) window.showNotification?.('Nie udało się otworzyć przesyłania. Spróbuj ponownie.', 'error');
                    else navigate(url);
                }
            } finally {
                pending = false;
                trigger?.removeAttribute('aria-busy');
            }
            if (files && !options.signal.aborted && modal?.querySelector('[data-document-upload-form]')) {
                setUploadFiles(files);
                modal.querySelector('[data-document-upload-form]').requestSubmit();
            }
        }

        document.addEventListener('click', event => {
            if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            if (modal && (event.target === modal || event.target.closest('[data-document-modal-close]'))) {
                event.preventDefault();
                event.stopImmediatePropagation();
                close();
                return;
            }
            const link = event.target.closest('a[data-document-modal]');
            if (!link || (link.target && link.target !== '_self')) return;
            event.preventDefault();
            openDialog(link.href, link);
        }, { ...options, capture: true });

        document.addEventListener('submit', async event => {
            const form = event.target.closest('[data-document-form]');
            if (!form || !host.contains(form)) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            if (pending || closing || form.dataset.saved === 'true') return;
            pending = true;
            const formData = new FormData(form);
            let editorTab = null;
            if (form.hasAttribute('data-office-create')) {
                // Reserve the tab during the user's click, before the asynchronous save.
                editorTab = window.open('about:blank', '_blank');
                if (editorTab) {
                    editorTab.opener = null;
                    editorTab.document.title = 'Otwieranie dokumentu | Ancore';
                    editorTab.document.body.textContent = 'Tworzenie dokumentu…';
                }
            }
            const submit = form.querySelector('[type="submit"]');
            const errorMessage = form.querySelector('[data-document-modal-error]');
            submit.disabled = true;
            form.setAttribute('aria-busy', 'true');
            errorMessage.hidden = true;
            try {
                const response = await fetch(form.action, {
                    method: 'POST', body: formData,
                    headers: { 'X-Document-Modal': 'true' }, signal: options.signal,
                });
                if (!response.ok || response.redirected) throw new Error('Unable to save document');
                if (response.headers.get('Content-Type')?.includes('application/json')) {
                    const result = await response.json();
                    if (!options.signal.aborted) {
                        if (result.editor_url) {
                            if (editorTab && !editorTab.closed) {
                                editorTab.location.replace(result.editor_url);
                                editorTab = null;
                            } else {
                                // A blocked or manually closed tab must not cause a duplicate creation.
                                form.dataset.saved = 'true';
                                form.querySelectorAll('.documents-field').forEach(field => field.remove());
                                submit.remove();
                                modal.querySelector('h2').textContent = 'Dokument utworzony';
                                errorMessage.textContent = 'Dokument został zapisany. Otwórz edytor w nowej karcie.';
                                errorMessage.hidden = false;
                                const open = document.createElement('a');
                                open.href = result.editor_url;
                                open.target = '_blank';
                                open.rel = 'noopener';
                                open.className = 'btn btn-primary';
                                open.textContent = 'Otwórz edytor';
                                form.querySelector('.tasks-modal__footer').append(open);
                                const cancel = form.querySelector('.tasks-modal__footer [data-document-modal-close]');
                                cancel.textContent = 'Wróć do dokumentów';
                                modal.dataset.returnUrl = result.redirect_url;
                                directLink = true;
                                open.focus();
                                return;
                            }
                        }
                        pending = false;
                        modal.remove();
                        modal = null;
                        restoreBackground();
                        navigate(result.redirect_url);
                    }
                } else {
                    const html = await response.text();
                    if (!options.signal.aborted) replaceDialog(html);
                }
            } catch (error) {
                if (!options.signal.aborted) {
                    errorMessage.textContent = 'Nie udało się zapisać zmian. Sprawdź połączenie i spróbuj ponownie.';
                    errorMessage.hidden = false;
                    errorMessage.scrollIntoView({ block: 'nearest' });
                }
            } finally {
                if (editorTab && !editorTab.closed) editorTab.close();
                pending = false;
                submit.disabled = false;
                form.removeAttribute('aria-busy');
            }
        }, { ...options, capture: true });

        document.addEventListener('keydown', event => {
            if (!modal || event.defaultPrevented) return;
            if (event.key === 'Escape') {
                event.preventDefault();
                event.stopImmediatePropagation();
                close();
            } else if (event.key === 'Tab') {
                const focusable = [...modal.querySelectorAll('a[href], button:not(:disabled), input:not([type="hidden"]), textarea, select, iframe, [tabindex="0"]')]
                    .filter(element => element.getClientRects().length && !element.closest('[inert]')
                        && !element.matches('[tabindex="-1"], [aria-hidden="true"], :disabled'));
                const first = focusable[0], last = focusable[focusable.length - 1];
                if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
                else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
            }
        }, { ...options, capture: true });
        options.signal.addEventListener('abort', restoreBackground, { once: true });
        if (modal) activate();
        return { openUpload: openDialog, setUploadFiles, isBusy: () => pending || closing };
    }

    function initDocumentDragDrop(options, modals) {
        const page = document.querySelector('[data-document-dnd]');
        if (!page || !modals) return;
        const mime = 'application/x-ancore-document';
        const status = document.createElement('p');
        status.className = 'documents-drag-status';
        status.setAttribute('role', 'status');
        status.hidden = true;
        page.append(status);
        let source = null, active = null, moving = false, suppressClickUntil = 0;
        let dragPreview = null, previewFrame = 0;
        const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

        function positionPreview(event) {
            if (!dragPreview || moving) return;
            const preview = dragPreview;
            preview.pointer = { x: event.clientX, y: event.clientY };
            preview.node.hidden = false;
            if (previewFrame) return;
            previewFrame = requestAnimationFrame(() => {
                previewFrame = 0;
                if (dragPreview !== preview) return;
                const { width, height } = preview.node.getBoundingClientRect();
                const { x, y } = preview.pointer;
                // Keep the opaque card beside the pointer, including near viewport edges.
                const left = x + width + 24 < window.innerWidth ? x + 18 : x - width - 18;
                const top = y + height + 24 < window.innerHeight ? y + 18 : y - height - 18;
                preview.node.style.transform = `translate3d(${Math.max(8, left)}px, ${Math.max(8, top)}px, 0)`;
            });
        }

        function createPreview(row, event) {
            const node = document.createElement('div');
            node.className = 'documents-drag-preview';
            node.setAttribute('aria-hidden', 'true');
            // The app zooms <html>; drag-event coordinates are viewport pixels.
            const scale = parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
            node.style.zoom = String(1 / scale);
            const card = document.createElement('div');
            card.className = 'documents-drag-preview__card';
            const icon = document.createElement('span');
            icon.className = 'documents-drag-preview__icon';
            const originalIcon = row.querySelector('.documents-card-preview svg, .documents-name .documents-file-icon svg');
            if (originalIcon) icon.append(originalIcon.cloneNode(true));
            const copy = document.createElement('div');
            copy.className = 'documents-drag-preview__copy';
            const name = document.createElement('span');
            name.className = 'documents-drag-preview__name';
            name.textContent = row.dataset.documentTitle;
            const meta = document.createElement('span');
            meta.className = 'documents-drag-preview__meta';
            meta.textContent = row.dataset.documentMeta;
            const hint = document.createElement('span');
            hint.className = 'documents-drag-preview__hint';
            hint.textContent = 'Wybierz folder docelowy';
            copy.append(name, meta);
            card.append(icon, copy, hint);
            node.append(card);
            // Replace Chrome's native link/URL thumbnail with a transparent drag image.
            const nativeImage = document.createElement('canvas');
            nativeImage.width = nativeImage.height = 1;
            nativeImage.className = 'documents-drag-native-image';
            nativeImage.setAttribute('aria-hidden', 'true');
            document.body.append(node, nativeImage);
            event.dataTransfer.setDragImage(nativeImage, 0, 0);
            dragPreview = { node, hint, nativeImage, pointer: { x: event.clientX, y: event.clientY } };
            positionPreview(event);
        }

        async function settlePreview(target) {
            if (!dragPreview || !target?.isConnected || reducedMotion.matches) return;
            cancelAnimationFrame(previewFrame);
            previewFrame = 0;
            const node = dragPreview.node;
            const rect = target.getBoundingClientRect();
            const previewRect = node.getBoundingClientRect();
            const left = rect.left + rect.width / 2 - previewRect.width * 0.1;
            const top = rect.top + rect.height / 2 - previewRect.height * 0.1;
            const animation = node.animate([
                { transform: node.style.transform, opacity: 1 },
                { transform: `translate3d(${left}px, ${top}px, 0) scale(0.2)`, opacity: 0 },
            ], { duration: 180, easing: 'cubic-bezier(0.2, 0.7, 0.2, 1)', fill: 'forwards' });
            try { await animation.finished; } catch (_) { /* Navigation may cancel the animation. */ }
        }

        function clear() {
            active?.classList.remove('is-document-drop-target');
            active = null;
            status.hidden = true;
        }

        function finish() {
            clear();
            cancelAnimationFrame(previewFrame);
            previewFrame = 0;
            dragPreview?.node.getAnimations().forEach(animation => animation.cancel());
            dragPreview?.node.remove();
            dragPreview?.nativeImage.remove();
            dragPreview = null;
            source?.classList.remove('is-document-dragging');
            source = null;
        }

        function hasFiles(event) {
            return Array.from(event.dataTransfer?.types || []).includes('Files');
        }

        function isMove(event) {
            return Array.from(event.dataTransfer?.types || []).includes(mime);
        }

        function destination(event) {
            if (moving || modals.isBusy()) return null;
            const dialog = document.querySelector('[data-document-dialog]');
            if (dialog) {
                return hasFiles(event) ? event.target.closest('[data-document-upload-form]') : null;
            }
            if (page.dataset.documentTrash === 'trash') return null;
            const target = event.target.closest('[data-document-drop]');
            if (!target || !page.contains(target) || target.closest('[inert]')) return null;
            if (source && (target === source || source.dataset.documentLocation === target.dataset.documentDrop)) return null;
            return target;
        }

        function indicate(event) {
            const target = destination(event);
            if (active !== target) {
                clear();
                active = target;
                target?.classList.add('is-document-drop-target');
            }
            event.dataTransfer.dropEffect = target ? (hasFiles(event) ? 'copy' : 'move') : 'none';
            if (dragPreview && !moving) {
                dragPreview.hint.textContent = target ? `Przenieś do: ${target.dataset.documentLabel}` : 'Wybierz folder docelowy';
                dragPreview.node.classList.toggle('has-drop-target', Boolean(target));
                positionPreview(event);
            }
            // The upload dialog already describes its destination.
            if (target?.hasAttribute('data-document-upload-form')) return;
            status.textContent = target
                ? `Upuść, aby ${hasFiles(event) ? 'przesłać pliki' : 'przenieść'} do: ${target.dataset.documentLabel}`
                : (page.dataset.documentTrash === 'trash' ? 'W koszu przeciąganie jest niedostępne.' : 'Upuść na folder lub wybrany dysk.');
            // The moving card already shows the destination next to its filename.
            status.hidden = Boolean(dragPreview || document.querySelector('[data-document-dialog]'));
        }

        page.addEventListener('dragstart', event => {
            const row = event.target.closest('[data-document-drag]');
            if (!row) return;
            if (moving || modals.isBusy() || event.target.closest('.documents-row-actions, [data-document-actions], button, input, select, textarea')) {
                event.preventDefault();
                return;
            }
            finish();
            source = row;
            event.dataTransfer.clearData();
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData(mime, JSON.stringify({
                scope: page.dataset.documentScope,
                url: row.dataset.documentMoveUrl,
                location: row.dataset.documentLocation,
                folder: row.dataset.documentDrop || '',
            }));
            createPreview(row, event);
            requestAnimationFrame(() => { if (source === row) row.classList.add('is-document-dragging'); });
        }, options);

        for (const name of ['dragenter', 'dragover']) {
            document.addEventListener(name, event => {
                if (!hasFiles(event) && !isMove(event)) return;
                event.preventDefault();
                indicate(event);
            }, options);
        }
        document.addEventListener('dragleave', event => {
            if (!event.relatedTarget) {
                clear();
                if (dragPreview && !moving) dragPreview.node.hidden = true;
            }
        }, options);
        document.addEventListener('dragend', () => {
            if (source) suppressClickUntil = Date.now() + 250;
            if (!moving) finish();
        }, options);
        document.addEventListener('keydown', event => { if (event.key === 'Escape' && !moving) finish(); }, options);
        window.addEventListener('blur', () => { if (!moving) finish(); }, options);
        page.addEventListener('click', event => {
            if (Date.now() < suppressClickUntil) {
                event.preventDefault();
                event.stopImmediatePropagation();
            }
        }, { ...options, capture: true });

        document.addEventListener('drop', async event => {
            if (!hasFiles(event) && !isMove(event)) return;
            event.preventDefault();
            const target = destination(event);
            const externalFiles = hasFiles(event);
            const files = Array.from(event.dataTransfer.files || []);
            const directories = Array.from(event.dataTransfer.items || []).some(item => item.webkitGetAsEntry?.()?.isDirectory);
            const payload = isMove(event) ? event.dataTransfer.getData(mime) : '';
            if (!target) { finish(); return; }
            if (externalFiles) {
                finish();
                if (directories || !files.length) {
                    window.showNotification?.('Przeciągnij pojedyncze pliki. Przesyłanie folderów z komputera nie jest obsługiwane.', 'error');
                    return;
                }
                if (target.hasAttribute('data-document-upload-form')) {
                    modals.setUploadFiles(files);
                    return;
                }
                const upload = new URL(page.dataset.documentUpload, window.location.href);
                const [type, id] = target.dataset.documentDrop.split(':');
                if (type === 'library' || type === 'folder') upload.searchParams.set(type, id);
                await modals.openUpload(upload.href, target, files);
                return;
            }
            let data;
            try { data = JSON.parse(payload); } catch (_) { finish(); return; }
            const scope = page.dataset.documentScope;
            if (!data || typeof data !== 'object' || data.scope !== scope || typeof data.url !== 'string' || !data.url.startsWith(scope)
                    || !/^(?:folders\/\d+|[0-9a-f-]{36})\/move\/$/.test(data.url.slice(scope.length))) {
                window.showNotification?.('Przenoś elementy w obrębie tego samego modułu i Workspace.', 'error');
                finish();
                return;
            }
            if (data.location === target.dataset.documentDrop || data.folder === target.dataset.documentDrop) { finish(); return; }
            const body = new FormData();
            body.set('target', target.dataset.documentDrop);
            body.set('csrfmiddlewaretoken', document.querySelector('[name="csrfmiddlewaretoken"]')?.value || '');
            moving = true;
            if (dragPreview) {
                dragPreview.node.hidden = false;
                dragPreview.hint.textContent = 'Przenoszenie…';
            }
            page.setAttribute('aria-busy', 'true');
            try {
                const response = await fetch(data.url, { method: 'POST', body,
                    headers: { 'X-Document-Move': 'true' }, signal: options.signal });
                if (response.redirected || !response.headers.get('Content-Type')?.includes('application/json')) {
                    throw new Error('Nie udało się przenieść elementu. Odśwież stronę i spróbuj ponownie.');
                }
                const result = await response.json();
                if (!response.ok) throw new Error(result.error || 'Nie udało się przenieść elementu.');
                if (!options.signal.aborted) await settlePreview(target);
                if (!options.signal.aborted) {
                    finish();
                    if (window.AncoreApp?.canNavigatePartially?.(window.location.href)) await window.AncoreApp.navigate(window.location.href);
                    else window.location.reload();
                }
            } catch (error) {
                if (!options.signal.aborted) window.showNotification?.(error instanceof TypeError
                    ? 'Nie udało się przenieść elementu. Sprawdź połączenie i spróbuj ponownie.'
                    : error.message || 'Nie udało się przenieść elementu.', 'error');
            } finally {
                moving = false;
                finish();
                page.removeAttribute('aria-busy');
            }
        }, options);
        options.signal.addEventListener('abort', () => { finish(); status.remove(); }, { once: true });
    }

    function initDocumentSidebar(options) {
        const page = document.querySelector('.documents-page');
        const sidebar = page?.querySelector('[data-documents-sidebar]');
        const toggle = page?.querySelector('[data-documents-sidebar-toggle]');
        const backdrop = page?.querySelector('[data-documents-sidebar-backdrop]');
        if (!sidebar || !toggle || !backdrop) return;
        const compact = window.matchMedia('(max-width: 1100px)');
        const storageKey = 'ancore:documents:sidebar-collapsed:v1';
        let collapsed = false;
        try { collapsed = localStorage.getItem(storageKey) === 'true'; } catch (_) {}
        let open = false;

        function update(restoreFocus = false) {
            const overlayOpen = compact.matches && open;
            const expanded = compact.matches ? open : !collapsed;
            page.classList.toggle('is-sidebar-open', overlayOpen);
            page.classList.toggle('is-sidebar-collapsed', !compact.matches && collapsed);
            toggle.setAttribute('aria-expanded', String(expanded));
            const label = expanded ? 'Ukryj panel dysków' : 'Pokaż panel dysków';
            toggle.setAttribute('aria-label', label);
            toggle.title = label;
            const focusHidden = !expanded && sidebar.contains(document.activeElement);
            sidebar.inert = !expanded;
            backdrop.hidden = !overlayOpen;
            if (overlayOpen) {
                sidebar.setAttribute('role', 'dialog');
                sidebar.setAttribute('aria-modal', 'true');
            } else {
                sidebar.removeAttribute('role');
                sidebar.removeAttribute('aria-modal');
            }
            if (restoreFocus || focusHidden) toggle.focus();
        }
        function close() { open = false; update(true); }
        toggle.addEventListener('click', () => {
            if (compact.matches) {
                open = !open;
            } else {
                collapsed = !collapsed;
                try { localStorage.setItem(storageKey, String(collapsed)); } catch (_) {}
            }
            update();
            if (compact.matches && open) sidebar.querySelector('[data-documents-sidebar-close]').focus();
        }, options);
        sidebar.querySelector('[data-documents-sidebar-close]').addEventListener('click', close, options);
        backdrop.addEventListener('click', close, options);
        sidebar.addEventListener('keydown', event => {
            if (!open || !compact.matches) return;
            if (event.key === 'Escape') { event.preventDefault(); close(); }
            if (event.key !== 'Tab') return;
            const links = [...sidebar.querySelectorAll('a[href], button:not([disabled])')];
            const first = links[0], last = links[links.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault(); last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault(); first.focus();
            }
        }, options);
        compact.addEventListener('change', () => { open = false; update(); }, options);
        update();
    }

    document.addEventListener('ancore:content-loaded', initDocuments);
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDocuments, { once: true });
    } else {
        initDocuments();
    }
})();
