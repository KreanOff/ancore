(function () {
    let controller;

    function initOffice() {
        controller?.abort();
        controller = new AbortController();
        const options = { signal: controller.signal };
        document.querySelector('[data-office-catalog]')?.addEventListener('submit', event => {
            const target = event.target.closest('[data-document-confirm]');
            if (!target || !window.showConfirmModal) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            window.showConfirmModal({
                title: 'Potwierdź operację', message: target.dataset.documentConfirm,
                confirmText: 'Potwierdź', confirmClass: 'btn-primary',
                onConfirm: () => HTMLFormElement.prototype.submit.call(target),
            });
        }, { ...options, capture: true });
        const form = document.querySelector('[data-office-editor]');
        if (!form) return;
        const editor = form.querySelector('[data-office-content]');
        const source = form.elements.content;
        const toolbar = form.querySelector('[data-office-toolbar]');
        const status = form.querySelector('[data-office-status]');
        const errorBox = form.querySelector('[data-office-errors]');
        const saveButton = form.querySelector('[data-office-save]');
        const download = form.querySelector('[data-office-download]');
        let pending = false;
        let savedRange;

        // The template remains inert. Copy only the attribute-free editor format.
        function safeFragment(html) {
            const template = document.createElement('template');
            template.innerHTML = html;
            const allowed = new Set(['p', 'br', 'h1', 'h2', 'h3', 'strong', 'em', 'u', 's', 'ul', 'ol', 'li', 'blockquote']);
            const blocked = new Set(['script', 'style', 'iframe', 'object', 'svg', 'math', 'template']);
            const aliases = { div: 'p', b: 'strong', i: 'em', strike: 's' };
            function copyNodes(from, to, depth = 0) {
                if (depth > 64) return;
                for (const child of from.childNodes) {
                    if (child.nodeType === Node.TEXT_NODE) to.append(document.createTextNode(child.textContent));
                    else if (child.nodeType === Node.ELEMENT_NODE) {
                        const name = child.localName;
                        if (blocked.has(name)) continue;
                        const tag = aliases[name] || name;
                        if (allowed.has(tag)) {
                            const clean = document.createElement(tag);
                            copyNodes(child, clean, depth + 1);
                            to.append(clean);
                        } else copyNodes(child, to, depth + 1);
                    }
                }
            }
            const result = document.createDocumentFragment();
            copyNodes(template.content, result);
            return result;
        }

        editor.replaceChildren(safeFragment(source.value));
        source.hidden = true;
        editor.hidden = false;
        toolbar.hidden = false;
        function signature() {
            return JSON.stringify([form.elements.title.value, editor.innerHTML]);
        }
        let savedSignature = errorBox.hidden ? signature() : '';
        let dirty = !errorBox.hidden;
        function update() {
            dirty = signature() !== savedSignature;
            source.value = editor.innerHTML;
            const text = editor.innerText.trim();
            const words = text ? text.split(/\s+/u).length : 0;
            form.querySelector('[data-office-word-count]').textContent = `Liczba słów: ${words}`;
            if (!pending && dirty) status.textContent = 'Niezapisane zmiany';
            if (download) {
                download.setAttribute('aria-disabled', String(dirty || pending));
                download.title = dirty ? 'Zapisz zmiany przed pobraniem' : 'Pobierz DOCX';
            }
        }
        update();
        form.addEventListener('input', update, options);
        form.addEventListener('change', update, options);

        function selectionInside() {
            const selection = window.getSelection();
            return selection?.rangeCount && editor.contains(selection.anchorNode) && editor.contains(selection.focusNode);
        }
        document.addEventListener('selectionchange', () => {
            if (!selectionInside()) return;
            savedRange = window.getSelection().getRangeAt(0).cloneRange();
            toolbar.querySelectorAll('[aria-pressed]').forEach(button => {
                button.setAttribute('aria-pressed', String(document.queryCommandState(button.dataset.officeCommand)));
            });
            const block = document.queryCommandValue('formatBlock').toLowerCase().replace(/[<>]/g, '');
            const select = toolbar.querySelector('[data-office-block]');
            const nextValue = [...select.options].some(option => option.value === block) ? block : 'p';
            if (select.value !== nextValue) {
                select.value = nextValue;
                window.AncoreCustomSelect?.refresh(toolbar);
            }
        }, options);
        function restoreSelection() {
            editor.focus();
            if (savedRange && editor.contains(savedRange.commonAncestorContainer)) {
                const selection = window.getSelection();
                selection.removeAllRanges();
                selection.addRange(savedRange);
            }
        }
        toolbar.addEventListener('mousedown', event => {
            if (event.target.closest('button')) event.preventDefault();
        }, options);
        toolbar.addEventListener('click', event => {
            const button = event.target.closest('[data-office-command]');
            if (!button) return;
            restoreSelection();
            document.execCommand(button.dataset.officeCommand, false);
            update();
        }, options);
        toolbar.querySelector('[data-office-block]').addEventListener('change', event => {
            restoreSelection();
            document.execCommand('formatBlock', false, event.target.value);
            update();
        }, options);
        editor.addEventListener('paste', event => {
            event.preventDefault();
            document.execCommand('insertText', false, event.clipboardData.getData('text/plain'));
            update();
        }, options);
        // Files are handled by the catalog upload. Do not insert active dragged HTML.
        editor.addEventListener('drop', event => { event.preventDefault(); }, options);
        editor.addEventListener('dragover', event => { event.preventDefault(); }, options);

        function showError(text) {
            errorBox.textContent = text;
            errorBox.hidden = false;
            status.textContent = 'Nie zapisano zmian';
        }
        form.addEventListener('submit', async event => {
            event.preventDefault();
            if (pending || !form.reportValidity()) return;
            update();
            const submittedSignature = signature();
            pending = true;
            saveButton.disabled = true;
            form.setAttribute('aria-busy', 'true');
            errorBox.hidden = true;
            status.textContent = 'Zapisywanie…';
            try {
                const response = await fetch(form.action || window.location.href, {
                    method: 'POST', body: new FormData(form),
                    headers: { 'X-Office-Editor': 'true' }, signal: options.signal,
                });
                if (response.redirected || !response.headers.get('Content-Type')?.includes('application/json')) throw new Error('session');
                const result = await response.json();
                if (!response.ok) {
                    const errors = Object.values(result.errors || {}).flat().map(error => error.message).join(' ');
                    showError(errors || 'Nie udało się zapisać dokumentu. Spróbuj ponownie.');
                    return;
                }
                form.elements.revision.value = result.revision;
                form.action = result.url;
                form.dataset.new = 'false';
                window.history.replaceState(window.history.state, '', result.url);
                document.title = `${result.title} | Dokumenty | ancore`;
                form.querySelector('h1').textContent = 'Edytuj dokument';
                if (download) {
                    download.href = `${result.url}download/`;
                    download.hidden = false;
                }
                savedSignature = submittedSignature;
                status.textContent = `Zapisano o ${result.saved_at}`;
            } catch (error) {
                if (!options.signal.aborted) showError('Nie udało się zapisać zmian. Sprawdź połączenie i zalogowanie, a następnie spróbuj ponownie. Twoja treść pozostaje w edytorze.');
            } finally {
                pending = false;
                saveButton.disabled = false;
                form.removeAttribute('aria-busy');
                update();
            }
        }, options);
        document.addEventListener('keydown', event => {
            if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
                event.preventDefault();
                form.requestSubmit();
            }
        }, options);
        download?.addEventListener('click', event => {
            if (dirty || pending) {
                event.preventDefault();
                showError('Zapisz zmiany przed pobraniem dokumentu.');
            }
        }, options);
        window.addEventListener('beforeunload', event => {
            if (!dirty && !pending) return;
            event.preventDefault();
            event.returnValue = '';
        }, options);
    }

    document.addEventListener('DOMContentLoaded', initOffice);
    document.addEventListener('ancore:content-loaded', initOffice);
    if (document.readyState !== 'loading') initOffice();
}());
