(() => {
    if (window.ancoreTaskFiltersLoaded) return;
    window.ancoreTaskFiltersLoaded = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        const page = document.querySelector('.task-filters-page');
        const host = document.querySelector('[data-filter-modal-host]');
        if (!page || !host) return;
        let pending = false;
        let discard = false;
        let initial = '';
        let previousFocus;
        let background = [];
        const modal = () => host.querySelector('[data-filter-modal]');
        const values = () => JSON.stringify([...new FormData(host.querySelector('form'))].filter(([name]) => name !== 'csrfmiddlewaretoken'));
        const dirty = () => modal() && values() !== initial;
        const navigate = async (url, replace = false) => {
            if (window.AncoreApp?.navigate) await window.AncoreApp.navigate(url, { replace });
            else window.location.href = url;
        };
        function restoreBackground() {
            background.forEach(element => { element.inert = false; });
            background = [];
        }
        function updateFields() {
            const visibility = host.querySelector('[name="visibility"]');
            const sharing = host.querySelector('[data-filter-field="shared_with"]');
            if (visibility && sharing) sharing.hidden = visibility.value !== 'selected';
        }
        async function request(url, options = {}) {
            const response = await fetch(url, {
                ...options, credentials: 'same-origin', headers: { 'X-Filter-Modal': 'true' },
                signal: AbortSignal.any([signal, AbortSignal.timeout(15000)]),
            });
            if (response.redirected) throw new Error('Sesja wygasła. Odśwież stronę i zaloguj się ponownie.');
            const data = await response.json();
            if (!response.ok && !(response.status === 400 && data.html)) throw new Error(data.error || 'Nie udało się zapisać zmiany. Spróbuj ponownie.');
            return data;
        }
        function display(html, preserve = false) {
            restoreBackground();
            host.innerHTML = html;
            if (!modal()) throw new Error('Brak formularza filtra.');
            if (!preserve) initial = values();
            window.AncoreIcons?.render(host);
            window.AncoreTaskModals.open(modal(), host.querySelector('[aria-invalid="true"], [name="name"]'));
            for (let node = host; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
                        sibling.inert = true;
                        background.push(sibling);
                    }
                });
            }
            updateFields();
        }
        document.addEventListener('click', async event => {
            const trigger = event.target.closest('[data-filter-open]');
            if (!trigger || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            if (pending || modal()) return;
            pending = true;
            previousFocus = trigger.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || trigger;
            trigger.setAttribute('aria-busy', 'true');
            try {
                const data = await request(trigger.href);
                if (!signal.aborted) display(data.html);
            } catch (error) {
                if (!signal.aborted) window.showNotification?.(error.message, 'error');
            } finally {
                pending = false;
                trigger.removeAttribute('aria-busy');
            }
        }, { capture: true, signal });
        host.addEventListener('submit', async event => {
            const form = event.target.closest('[data-filter-form]');
            if (!form) return;
            event.preventDefault();
            if (pending) return;
            const body = new FormData(form);
            body.set('return_to', host.dataset.filterReturnUrl);
            const controls = [...form.querySelectorAll('button, input, select, textarea')].map(control => [control, control.disabled]);
            pending = true;
            controls.forEach(([control]) => { control.disabled = true; });
            form.setAttribute('aria-busy', 'true');
            const errorBox = form.querySelector('[data-filter-error]');
            errorBox.hidden = true;
            try {
                const data = await request(form.action, { method: 'POST', body });
                if (signal.aborted) return;
                pending = false;
                if (data.saved) {
                    discard = true;
                    window.AncoreTaskModals.close(modal());
                    await navigate(data.url, true);
                } else display(data.html, true);
            } catch (error) {
                if (!signal.aborted) { errorBox.textContent = error.message; errorBox.hidden = false; }
            } finally {
                pending = false;
                controls.forEach(([control, disabled]) => { control.disabled = disabled; });
                window.AncoreCustomSelect?.refresh(form);
                form.removeAttribute('aria-busy');
            }
        }, { signal });
        page.addEventListener('submit', event => {
            const form = event.target.closest('[data-filter-search]');
            if (form) {
                event.preventDefault();
                navigate(form.action + '?' + new URLSearchParams(new FormData(form)));
                return;
            }
            const action = event.target.closest('[data-filter-action]');
            if (!action) return;
            event.preventDefault();
            if (pending) return;
            const execute = async () => {
                if (signal.aborted || pending) return;
                pending = true;
                const button = action.querySelector('button');
                button.disabled = true;
                try {
                    const data = await request(action.action, { method: 'POST', body: new FormData(action) });
                    pending = false;
                    if (!signal.aborted) await navigate(data.url, true);
                } catch (error) {
                    if (!signal.aborted) window.showNotification?.(error.message, 'error');
                } finally { pending = false; button.disabled = false; }
            };
            if (action.dataset.confirmName) window.showConfirmModal({
                title: 'Usuń filtr', message: window.escapeHtmlForModal('Usunąć „' + action.dataset.confirmName + '”?'),
                confirmText: 'Usuń', cancelText: 'Anuluj', confirmClass: 'btn-danger', onConfirm: execute,
            });
            else execute();
        }, { signal });
        host.addEventListener('change', updateFields, { signal });
        host.addEventListener('ancore:task-modal-before-close', event => {
            if (pending) { event.preventDefault(); return; }
            if (discard || !dirty()) return;
            event.preventDefault();
            window.showConfirmModal({
                title: 'Niezapisane zmiany', message: 'Zamknąć formularz bez zapisania zmian?',
                confirmText: 'Zamknij bez zapisu', cancelText: 'Wróć do edycji',
                onConfirm: () => { if (!signal.aborted) { discard = true; window.AncoreTaskModals.close(modal()); } },
            });
        }, { signal });
        host.addEventListener('ancore:task-modal-closed', () => {
            restoreBackground();
            host.replaceChildren();
            discard = false;
            previousFocus?.focus({ preventScroll: true });
            const url = new URL(host.dataset.filterReturnUrl, window.location.origin);
            if (window.location.pathname !== url.pathname) window.history.replaceState(window.history.state, '', url.href);
        }, { signal });
        document.addEventListener('ancore:before-navigate', event => {
            if (pending) { event.preventDefault(); return; }
            if (modal() && !discard && dirty()) { event.preventDefault(); window.AncoreTaskModals.close(modal()); }
        }, { signal });
        window.addEventListener('beforeunload', event => {
            if (dirty()) { event.preventDefault(); event.returnValue = ''; }
        }, { signal });
        signal.addEventListener('abort', restoreBackground, { once: true });
        if (modal()) display(host.innerHTML);
    }
    document.addEventListener('ancore:content-loaded', init);
    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
})();
