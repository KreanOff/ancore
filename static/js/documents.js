(function () {
    let controller;

    function initDocuments() {
        controller?.abort();
        controller = new AbortController();
        const options = { signal: controller.signal };
        initDocumentSidebar(options);
        initDocumentModals(options);
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

    function initDocumentModals(options) {
        const host = document.querySelector('[data-document-modal-host]');
        if (!host) return;
        let modal = host.querySelector('[data-document-dialog]');
        const directLink = Boolean(modal);
        let previousFocus;
        let pending = false;
        let inertElements = [];

        function restoreBackground() {
            document.body.classList.remove('contacts-photo-editor-open');
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
            window.AncorePhotoEditors?.init(modal);
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
                || modal.querySelector('input:not([type="hidden"]):not([type="file"]), textarea, select');
            (focusTarget || modal.querySelector('[data-document-modal-close]'))?.focus();
        }

        function navigate(url) {
            if (window.AncoreApp?.canNavigatePartially?.(url)) window.AncoreApp.navigate(url);
            else window.location.assign(url);
        }

        function close() {
            if (!modal || pending) return;
            const returnUrl = modal.dataset.returnUrl;
            modal.remove();
            modal = null;
            restoreBackground();
            if (directLink) navigate(returnUrl);
            else {
                const returnFocus = previousFocus?.closest('[data-section-actions]')?.querySelector('[data-section-menu-toggle]')
                    || (previousFocus?.closest('[inert]') ? document.querySelector('[data-documents-sidebar-toggle]') : previousFocus);
                if (returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
            }
        }

        function replaceDialog(html) {
            const parsed = new DOMParser().parseFromString(html, 'text/html');
            const next = parsed.querySelector('[data-document-dialog]');
            if (!next) throw new Error('Missing document dialog');
            // A validation error must not discard files already selected by the user.
            const photoEditor = modal?.querySelector('.documents-library-photo-field');
            const nextPhotoEditor = next.querySelector('.documents-library-photo-field');
            if (photoEditor && nextPhotoEditor && !nextPhotoEditor.querySelector('[role="alert"]')) {
                nextPhotoEditor.replaceWith(photoEditor);
            }
            const files = modal?.querySelector('input[type="file"]');
            const nextFiles = next.querySelector('input[type="file"]');
            if (files && nextFiles && !photoEditor) {
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

        document.addEventListener('click', async event => {
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
            if (pending || (modal && !modal.contains(link))) return;
            if (!modal) previousFocus = link;
            pending = true;
            link.setAttribute('aria-busy', 'true');
            document.querySelector('.documents-page.is-sidebar-open [data-documents-sidebar-close]')?.click();
            const menu = link.closest('[data-section-actions]');
            if (menu?.querySelector('[data-section-menu-toggle]')?.getAttribute('aria-expanded') === 'true') {
                menu.querySelector('[data-section-menu-toggle]').click();
            }
            try {
                const response = await fetch(link.href, { headers: { 'X-Document-Modal': 'true' }, signal: options.signal });
                if (!response.ok || response.redirected) throw new Error('Unable to load dialog');
                const html = await response.text();
                if (!options.signal.aborted) replaceDialog(html);
            } catch (error) {
                if (!options.signal.aborted) navigate(link.href);
            } finally {
                pending = false;
                link.removeAttribute('aria-busy');
            }
        }, { ...options, capture: true });

        document.addEventListener('submit', async event => {
            const form = event.target.closest('[data-document-form]');
            if (!form || !host.contains(form)) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            if (pending) return;
            pending = true;
            const submit = form.querySelector('[type="submit"]');
            const errorMessage = form.querySelector('[data-document-modal-error]');
            submit.disabled = true;
            form.setAttribute('aria-busy', 'true');
            errorMessage.hidden = true;
            try {
                const response = await fetch(form.action, {
                    method: 'POST', body: new FormData(form),
                    headers: { 'X-Document-Modal': 'true' }, signal: options.signal,
                });
                if (!response.ok || response.redirected) throw new Error('Unable to save document');
                if (response.headers.get('Content-Type')?.includes('application/json')) {
                    const result = await response.json();
                    if (!options.signal.aborted) {
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
                pending = false;
                submit.disabled = false;
                form.removeAttribute('aria-busy');
            }
        }, { ...options, capture: true });

        document.addEventListener('keydown', event => {
            if (!modal || event.defaultPrevented) return;
            if (modal.querySelector('[data-profile-photo-modal]:not([hidden])')) return;
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
