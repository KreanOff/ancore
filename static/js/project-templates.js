(function () {
    if (window.ancoreProjectTemplateModals) return;
    window.ancoreProjectTemplateModals = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;
        const host = document.querySelector('[data-project-template-modal-host]');
        if (!host) return;
        let pending = false;
        let closing = false;
        let changed = false;
        let previousFocus;
        let initialDetails = '';
        let discardConfirmed = false;
        let inertElements = [];
        let activeTab = 'sections';
        const mainModal = () => host.querySelector('[data-template-editor-modal]');
        const detailsForm = () => host.querySelector('[data-template-details-form]');
        const detailsValues = () => [...(detailsForm()?.elements || [])]
            .filter(field => field.name.startsWith('details-')).map(field => [field.name, field.value]);
        const hasUnsavedDetails = () => JSON.stringify(detailsValues()) !== initialDetails;

        function selectTab(name, focus = false) {
            const main = mainModal();
            const tabs = [...(main?.querySelectorAll('[data-template-tab]') || [])];
            const selected = tabs.find(tab => tab.dataset.templateTab === name);
            if (!selected) return;
            activeTab = name;
            tabs.forEach(tab => {
                const active = tab === selected;
                tab.setAttribute('aria-selected', String(active));
                tab.tabIndex = active ? 0 : -1;
            });
            main.querySelectorAll('[data-template-tab-panel]').forEach(panel => {
                panel.hidden = panel.dataset.templateTabPanel !== name;
            });
            main.querySelectorAll('[data-template-tab-action]').forEach(button => {
                button.hidden = button.dataset.templateTabAction !== name;
            });
            if (focus) selected.focus();
        }

        function restoreBackground() {
            inertElements.forEach(element => { element.inert = false; });
            inertElements = [];
        }

        function syncModalBackground() {
            const main = mainModal();
            if (!main?.classList.contains('is-open')) {
                restoreBackground();
                return;
            }
            for (let node = host; node && node !== document.body; node = node.parentElement) {
                [...node.parentElement.children].forEach(sibling => {
                    if (sibling !== node && sibling instanceof HTMLElement && !sibling.inert) {
                        sibling.inert = true;
                        inertElements.push(sibling);
                    }
                });
            }
            main.inert = [...host.querySelectorAll('.tasks-modal.is-open')].some(modal => modal !== main);
        }

        async function request(url, options = {}) {
            const requestController = new AbortController();
            const abort = () => requestController.abort();
            signal.addEventListener('abort', abort, { once: true });
            const timer = window.setTimeout(abort, 15000);
            try {
                const response = await fetch(url, {
                    ...options, credentials: 'same-origin', signal: requestController.signal,
                    headers: { 'X-Template-Modal': 'true', ...options.headers },
                });
                if (!response.ok || response.redirected) throw new Error('Template request failed');
                return await response.json();
            } finally {
                window.clearTimeout(timer);
                signal.removeEventListener('abort', abort);
            }
        }

        function displayEditor(html, preservedDetails) {
            const parsed = new DOMParser().parseFromString(html, 'text/html');
            const editor = parsed.querySelector('[data-project-template-editor]');
            if (!editor) throw new Error('Missing template editor');
            const activeChild = editor.querySelector('.tasks-modal.is-open');
            editor.querySelectorAll('.tasks-modal').forEach(modal => {
                modal.classList.remove('is-open');
                modal.setAttribute('aria-hidden', 'true');
            });
            host.replaceChildren(editor);
            selectTab(activeTab);
            initialDetails = JSON.stringify(detailsValues());
            for (const [name, value] of preservedDetails || []) {
                const field = detailsForm()?.elements.namedItem(name);
                if (field) field.value = value;
            }
            window.AncoreIcons?.render(host);
            window.AncoreCustomSelect?.refresh(host);
            document.dispatchEvent(new CustomEvent('ancore:modals-loaded', { detail: { root: host } }));
            const main = mainModal();
            window.AncoreTaskModals.open(main, main.querySelector('[aria-invalid="true"], input:not([type="hidden"])'));
            if (activeChild) {
                window.AncoreTaskModals.open(activeChild, activeChild.querySelector('[aria-invalid="true"], input:not([type="hidden"])'));
            }
        }

        async function openEditor(trigger) {
            if (pending || closing || mainModal()) return;
            previousFocus = trigger.closest('[data-row-actions]')?.querySelector('[data-row-actions-toggle]') || trigger;
            activeTab = 'sections';
            pending = true;
            trigger.setAttribute('aria-busy', 'true');
            try {
                const result = await request(trigger.dataset.templateUrl);
                if (!signal.aborted) displayEditor(result.html);
            } catch (error) {
                if (!signal.aborted) window.showNotification?.('Nie udało się otworzyć szablonu. Spróbuj ponownie.', 'error');
            } finally {
                pending = false;
                trigger.removeAttribute('aria-busy');
            }
        }

        async function saveEditor(form) {
            if (pending || closing || !form.isConnected) return;
            const body = new FormData(form);
            const savingDetails = form.matches('[data-template-details-form]');
            const preservedDetails = !savingDetails && hasUnsavedDetails() ? detailsValues() : null;
            const errorBox = form.closest('.tasks-modal').querySelector('[data-template-request-error]');
            errorBox.hidden = true;
            pending = true;
            form.setAttribute('aria-busy', 'true');
            const controls = [...host.querySelectorAll('button, input, textarea, select')].map(control => [control, control.disabled]);
            controls.forEach(([control]) => { control.disabled = true; });
            try {
                const result = await request(form.getAttribute('action'), { method: 'POST', body });
                if (signal.aborted) return;
                changed ||= result.saved;
                displayEditor(result.html, preservedDetails);
                if (result.saved) window.showNotification?.('Szablon zapisany.', 'success');
            } catch (error) {
                if (!signal.aborted) {
                    errorBox.textContent = 'Nie udało się zapisać zmian. Sprawdź połączenie i spróbuj ponownie.';
                    errorBox.hidden = false;
                }
            } finally {
                pending = false;
                form.removeAttribute('aria-busy');
                controls.forEach(([control, disabled]) => { control.disabled = disabled; });
            }
        }

        document.addEventListener('click', event => {
            const tab = event.target.closest('[data-template-tab]');
            if (tab && host.contains(tab)) {
                if (!pending && !closing) selectTab(tab.dataset.templateTab);
                return;
            }
            const trigger = event.target.closest('[data-open-project-template]');
            if (trigger) {
                event.preventDefault();
                openEditor(trigger);
                return;
            }
            const button = event.target.closest('[data-open-template-form]');
            if (!button || !host.contains(button) || pending || closing) return;
            const kind = button.dataset.openTemplateForm;
            const modal = host.querySelector(`#template-editor-${kind}`);
            const form = modal?.querySelector('[data-template-editor-form]');
            if (!form) return;
            form.reset();
            const values = { ...JSON.parse(form.dataset.templateFormDefaults), ...JSON.parse(button.dataset.templateFormValues || '{}') };
            const itemId = form.elements.namedItem(`${kind}-item_id`);
            if (itemId) itemId.value = '';
            for (const [name, value] of Object.entries(values)) {
                const input = form.elements.namedItem(`${kind}-${name}`);
                if (input) input.value = value ?? '';
            }
            modal.querySelectorAll('.tasks-modal__errors').forEach(box => { box.hidden = true; });
            window.AncoreTaskModals.open(modal, form.querySelector('input:not([type="hidden"])'));
        }, { signal });

        host.addEventListener('keydown', event => {
            const tab = event.target.closest('[data-template-tab]');
            if (!tab || pending || closing) return;
            const tabs = [...tab.parentElement.querySelectorAll('[data-template-tab]')];
            const index = tabs.indexOf(tab);
            let next;
            if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
            else if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
            else if (event.key === 'Home') next = 0;
            else if (event.key === 'End') next = tabs.length - 1;
            else return;
            event.preventDefault();
            selectTab(tabs[next].dataset.templateTab, true);
        }, { signal });

        document.addEventListener('submit', event => {
            const form = event.target;
            const isEditorForm = host.contains(form);
            const isDelete = form.matches('[data-delete-project-template], [data-delete-template-item]');
            if (!isEditorForm && !isDelete) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            if (pending || closing) return;
            if (!isDelete) {
                saveEditor(form);
                return;
            }
            const kind = form.dataset.deleteTemplateItem;
            const itemLabel = kind === 'section' ? 'grupę' : 'zadanie';
            window.showConfirmModal({
                title: kind ? `Usuń ${itemLabel}` : 'Usuń szablon projektu',
                message: kind ? (kind === 'section' ? 'Usunąć grupę wraz z jej zadaniami i podzadaniami z szablonu?' : 'Usunąć zadanie wraz z jego podzadaniami z szablonu?') : 'Usunąć szablon? Utworzone z niego projekty pozostaną bez zmian.',
                confirmText: kind ? `Usuń ${itemLabel}` : 'Usuń szablon', cancelText: 'Anuluj', confirmClass: 'btn-danger',
                onConfirm: () => { if (!signal.aborted) isEditorForm ? saveEditor(form) : form.submit(); },
            });
        }, { signal, capture: true });

        host.addEventListener('ancore:task-modal-opened', syncModalBackground, { signal });
        host.addEventListener('ancore:task-modal-before-close', event => {
            if (pending || closing) { event.preventDefault(); return; }
            if (event.target !== mainModal() || discardConfirmed || !hasUnsavedDetails()) return;
            event.preventDefault();
            window.showConfirmModal({
                title: 'Niezapisane zmiany', message: 'Zamknąć edytor bez zapisania nazwy i opisu szablonu?',
                confirmText: 'Zamknij bez zapisu', cancelText: 'Wróć do edycji',
                onConfirm: () => {
                    if (signal.aborted) return;
                    discardConfirmed = true;
                    window.AncoreTaskModals.close(mainModal());
                },
            });
        }, { signal });
        host.addEventListener('ancore:task-modal-closed', async event => {
            syncModalBackground();
            if (event.target !== mainModal()) return;
            closing = true;
            const modal = event.target;
            const panel = modal.querySelector('.tasks-modal__dialog');
            await Promise.allSettled([...modal.getAnimations(), ...panel.getAnimations()].map(animation => animation.finished));
            if (signal.aborted) return;
            host.replaceChildren();
            closing = false;
            discardConfirmed = false;
            if (changed) {
                const url = window.location.href;
                const templateId = previousFocus?.closest('[data-template-id]')?.dataset.templateId;
                if (window.AncoreApp?.canNavigatePartially?.(url)) {
                    await window.AncoreApp.navigate(url, { replace: true, updateHistory: false });
                    document.querySelector(`[data-template-id="${templateId}"] [data-row-actions-toggle]`)?.focus({ preventScroll: true });
                } else window.location.reload();
            } else if (previousFocus?.isConnected) previousFocus.focus({ preventScroll: true });
        }, { signal });
        signal.addEventListener('abort', restoreBackground, { once: true });
        if (host.firstElementChild) displayEditor(host.innerHTML);
    }

    if (!window.AncoreTaskModals) document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
