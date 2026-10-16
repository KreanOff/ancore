(function () {
    if (window.ancoreResourcesLoaded) return;
    window.ancoreResourcesLoaded = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        if (document.querySelector('[data-react-root="resources"]')) return;
        const page = document.querySelector('[data-resources-page]');
        const host = document.querySelector('[data-resource-modal-host]');
        if (!page || !host) return;
        const selectAll = page.querySelector('[data-resource-select-all]');
        const selections = [...page.querySelectorAll('[data-resource-select]')];
        function updateSelection() {
            const selected = selections.filter(input => input.checked);
            selections.forEach(input => input.closest('.resources-row').classList.toggle('checked', input.checked));
            if (selectAll) {
                selectAll.checked = selections.length > 0 && selected.length === selections.length;
                selectAll.indeterminate = selected.length > 0 && selected.length < selections.length;
                selectAll.disabled = !selections.length;
            }
        }
        selectAll?.addEventListener('change', () => {
            selections.forEach(input => { input.checked = selectAll.checked; });
            updateSelection();
        }, { signal });
        selections.forEach(input => input.addEventListener('change', updateSelection, { signal }));
        updateSelection();

        let pending = false;
        let discard = false;
        let initial = '';
        let previousFocus;
        let background = [];
        const modal = () => host.querySelector('[data-resource-modal]');
        const values = () => JSON.stringify([...new FormData(host.querySelector('form'))]);
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
                headers: { 'X-Resource-Modal': 'true' },
            });
            if (response.redirected || (!response.ok && response.status !== 400)) throw new Error('Resource request failed');
            return response.json();
        }

        function display(html, preserveInitial = false) {
            restoreBackground();
            host.innerHTML = html;
            if (!modal()) throw new Error('Missing resource form');
            if (!preserveInitial) initial = values();
            window.AncoreIcons?.render(host);
            window.AncoreTaskModals.open(modal(), host.querySelector('[aria-invalid="true"], input:not([type="hidden"])'));
            disableBackground();
        }

        async function refresh(url) {
            if (!await window.AncoreApp?.navigate(url, { replace: true, updateHistory: false })) window.location.href = url;
        }

        document.addEventListener('click', async event => {
            const trigger = event.target.closest('[data-resource-open]');
            if (!trigger || !page.contains(trigger) || event.button || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
            event.preventDefault();
            if (pending || modal()) return;
            pending = true;
            previousFocus = trigger.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || trigger;
            trigger.setAttribute('aria-busy', 'true');
            try {
                const result = await request(trigger.href);
                if (!signal.aborted) display(result.html);
            } catch (error) {
                if (!signal.aborted) window.showNotification?.('Nie udało się otworzyć zasobu. Spróbuj ponownie.', 'error');
            } finally {
                pending = false;
                trigger.removeAttribute('aria-busy');
            }
        }, { signal, capture: true });

        host.addEventListener('submit', async event => {
            const form = event.target.closest('[data-resource-form]');
            if (!form) return;
            event.preventDefault();
            if (pending) return;
            const body = new FormData(form);
            const controls = [...form.querySelectorAll('button, input, select, textarea')].map(control => [control, control.disabled]);
            const errorBox = form.querySelector('[data-resource-error]');
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
                    window.showNotification?.('Zasób zapisany.', 'success');
                } else display(result.html, true);
            } catch (error) {
                if (!signal.aborted) {
                    errorBox.textContent = 'Nie udało się zapisać zasobu. Sprawdź połączenie i spróbuj ponownie.';
                    errorBox.hidden = false;
                }
            } finally {
                pending = false;
                controls.forEach(([control, disabled]) => { control.disabled = disabled; });
                form.removeAttribute('aria-busy');
            }
        }, { signal });

        page.addEventListener('submit', event => {
            const form = event.target.closest('[data-resource-delete]');
            if (!form) return;
            event.preventDefault();
            if (pending) return;
            window.showConfirmModal({
                title: 'Usuń zasób',
                message: window.escapeHtmlForModal(`Usunąć zasób „${form.dataset.resourceName}”? Tej operacji nie można cofnąć.`),
                confirmText: 'Usuń zasób', cancelText: 'Anuluj', confirmClass: 'btn-danger',
                onConfirm: async () => {
                    if (signal.aborted || pending) return;
                    pending = true;
                    const button = form.querySelector('button');
                    button.disabled = true;
                    try {
                        const result = await request(form.action, { method: 'POST', body: new FormData(form) });
                        if (!signal.aborted) {
                            await refresh(result.url);
                            window.showNotification?.('Zasób usunięty.', 'success');
                        }
                    } catch (error) {
                        if (!signal.aborted) window.showNotification?.('Nie udało się usunąć zasobu. Spróbuj ponownie.', 'error');
                    } finally { pending = false; button.disabled = false; }
                },
            });
        }, { signal });

        host.addEventListener('ancore:task-modal-before-close', event => {
            if (pending) { event.preventDefault(); return; }
            if (discard || !dirty()) return;
            event.preventDefault();
            window.showConfirmModal({
                title: 'Niezapisane zmiany', message: 'Zamknąć zasób bez zapisania zmian?',
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
            const list = new URL(page.dataset.resourceListUrl, window.location.origin);
            if (window.location.pathname !== list.pathname) window.history.replaceState(window.history.state, '', list.href);
        }, { signal });
        document.addEventListener('ancore:before-navigate', event => {
            if (!modal()) return;
            if (pending || dirty()) {
                event.preventDefault();
                window.AncoreTaskModals.close(modal());
            }
        }, { signal });
        window.addEventListener('beforeunload', event => {
            if (dirty()) { event.preventDefault(); event.returnValue = ''; }
        }, { signal });
        signal.addEventListener('abort', restoreBackground, { once: true });
        if (modal()) display(host.innerHTML);
    }
    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
