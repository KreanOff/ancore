(() => {
    function initTitle(root, csrf) {
        const title = root.querySelector('[data-suite-title]');
        if (!title) return;
        const button = title.querySelector('[data-suite-title-button]');
        const input = title.querySelector('[data-suite-title-input]');
        const error = root.querySelector('[data-suite-title-error]');
        const status = root.querySelector('[data-suite-title-status]');
        let savedTitle = input.value, editing = false, saving = false;
        function setStatus(state) {
            if (status.dataset.state === state) return;
            const states = {
                saved: 'Nazwa zapisana',
                changed: 'Nazwa do zapisania',
                saving: 'Zapisywanie nazwy…',
                error: 'Błąd zapisu nazwy',
            };
            status.dataset.state = state;
            status.textContent = states[state];
        }
        function resize() { input.size = Math.max(12, Math.min(60, Array.from(input.value).length + 1)); }
        function clearError() { error.hidden = true; input.removeAttribute('aria-invalid'); }
        function finish(returnFocus) {
            editing = false;
            input.hidden = true;
            button.hidden = false;
            input.value = savedTitle;
            clearError();
            setStatus('saved');
            if (returnFocus) button.focus();
        }
        function begin() {
            if (editing || saving) return;
            editing = true;
            button.hidden = true;
            input.hidden = false;
            resize();
            input.focus();
            input.select();
        }
        button.addEventListener('click', begin);
        async function persist(returnFocus = false) {
            if (!editing || saving) return;
            const value = input.value.trim();
            if (value === savedTitle) { finish(returnFocus); return; }
            clearError();
            if (!value) {
                error.textContent = 'Podaj nazwę pliku.';
                error.hidden = false;
                input.setAttribute('aria-invalid', 'true');
                setStatus('error');
                if (returnFocus) input.focus();
                return;
            }
            saving = true;
            input.readOnly = true;
            title.setAttribute('aria-busy', 'true');
            setStatus('saving');
            let message = 'Nie udało się zapisać nazwy. Sprawdź połączenie i spróbuj ponownie.';
            try {
                const response = await fetch(title.dataset.renameUrl, {
                    method: 'POST', headers: {'X-CSRFToken': csrf, 'Accept': 'application/json'},
                    body: new URLSearchParams({title: value}), keepalive: true,
                });
                if (response.redirected || !response.headers.get('content-type')?.includes('application/json')) throw new Error();
                const data = await response.json();
                if (!response.ok) { message = data.error || message; throw new Error(); }
                savedTitle = data.title;
                button.textContent = savedTitle;
                button.title = `Zmień nazwę: ${savedTitle}`;
                button.setAttribute('aria-label', button.title);
                document.title = savedTitle + title.dataset.pageTitleSuffix;
                finish(returnFocus && document.activeElement === input);
            } catch {
                error.textContent = message;
                error.hidden = false;
                input.setAttribute('aria-invalid', 'true');
                setStatus('error');
            } finally {
                saving = false;
                input.readOnly = false;
                title.removeAttribute('aria-busy');
            }
        }
        input.addEventListener('input', () => {
            clearError();
            resize();
            setStatus(input.value.trim() === savedTitle ? 'saved' : 'changed');
        });
        input.addEventListener('blur', () => persist());
        input.addEventListener('keydown', event => {
            if (event.isComposing || !['Enter', 'Escape'].includes(event.key)) return;
            event.preventDefault();
            if (saving) return;
            if (event.key === 'Escape') finish(true);
            else persist(true);
        });
    }

    function init() {
        if (document.querySelector('[data-react-root="page"]')) return;
        const root = document.querySelector('[data-office-suite]');
        if (!root || root.dataset.initialized) return;
        root.dataset.initialized = 'true';
        const status = root.querySelector('[data-suite-status]');
        const error = root.querySelector('[data-suite-error]');
        const errorMessage = root.querySelector('[data-suite-error-message]');
        const retry = root.querySelector('[data-suite-retry]');
        const csrf = root.querySelector('[name=csrfmiddlewaretoken]').value;
        initTitle(root, csrf);
        const frame = root.querySelector('[data-board-frame]');
        let revision = Number(root.dataset.revision), pending = false, boardDirty = false;
        function fail(message, canRetry = false) { errorMessage.textContent = message; retry.hidden = !canRetry; error.hidden = false; }
        function clearError() { error.hidden = true; retry.hidden = true; }
        if (frame) {
            let boardReady = false;
            window.addEventListener('message', event => {
                if (event.origin !== location.origin || event.source !== frame.contentWindow || event.data?.source !== 'ancore-board') return;
                const data = event.data;
                if (data.type === 'status') {
                    status.textContent = data.message;
                    boardDirty = data.dirty;
                    boardReady = true;
                    if (!data.dirty) clearError();
                } else if (data.type === 'error') {
                    fail(data.message, true);
                    boardReady = true;
                }
            });
            retry.addEventListener('click', () => {
                if (boardReady) frame.contentWindow.postMessage({source: 'ancore', type: 'save'}, location.origin);
            });
            window.addEventListener('beforeunload', event => {
                if (boardDirty) { event.preventDefault(); event.returnValue = ''; }
            });
            setTimeout(() => { if (!boardReady) fail('Nie udało się załadować tablicy. Odśwież stronę i sprawdź połączenie.'); }, 20000);
            return;
        }
        const holder = root.querySelector('[data-api-url]');
        if (!holder) { status.textContent = 'Dokument zapisany'; return; }
        const life = new AbortController(), timeouts = new Set();
        function delay(action, time) {
            const id = setTimeout(() => { timeouts.delete(id); if (!life.signal.aborted) action(); }, time);
            timeouts.add(id);
            return id;
        }
        let editor, pollTimer, autoSaveTimer, editGeneration = 0, savingGeneration = 0, saveAttempt = 0, sessionInvalid = false, requesting = false, queued = false;
        function saveQueued() {
            if (queued && !pending && !requesting && editGeneration > savingGeneration) void persist();
        }
        async function poll() {
            try {
                const response = await fetch(root.dataset.stateUrl, {headers: {'Accept': 'application/json'}, cache: 'no-store', signal: life.signal});
                if (!response.ok || response.redirected) throw new Error();
                const data = await response.json();
                if (life.signal.aborted || sessionInvalid) return;
                if (data.key !== config.document.key) {
                    sessionInvalid = true;
                    pending = false;
                    queued = false;
                    clearTimeout(autoSaveTimer);
                    status.textContent = 'Sesja dokumentu zmieniła się';
                    fail('Plik został podmieniony lub sesja zakończona. Pobierz swoje zmiany z menu Plik edytora i otwórz aktualną wersję w nowej karcie.');
                    return;
                }
                if (data.save_error) { queued = false; fail('Nie udało się zapisać pliku w Ancore. Pozostaw edytor otwarty i spróbuj zapisać ponownie.', true); return; }
                if (data.revision > revision) {
                    revision = data.revision;
                    pending = false;
                    clearError();
                    status.textContent = savingGeneration === editGeneration ? `Zapisano w Ancore ${data.saved_at}` : 'Nowsze zmiany w edytorze';
                    saveQueued();
                }
            } catch { if (pending && !life.signal.aborted) fail('Brak potwierdzenia zapisu. Sprawdź połączenie i ponów zapis.', true); }
        }
        async function persist() {
            if (sessionInvalid || life.signal.aborted) return;
            if (pending || requesting) { queued = editGeneration > savingGeneration; return; }
            queued = false;
            requesting = true;
            pending = true;
            const attempt = ++saveAttempt;
            savingGeneration = editGeneration;
            status.textContent = 'Zapisywanie w Ancore…';
            clearError();
            try {
                const response = await fetch(root.dataset.saveUrl, {method: 'POST', headers: {'X-CSRFToken': csrf, 'X-Office-Key': config.document.key, 'Accept': 'application/json'}, signal: life.signal});
                const data = await response.json();
                if (life.signal.aborted || sessionInvalid) return;
                if (!response.ok) throw new Error(data.error);
                if (!data.pending) { pending = false; status.textContent = 'Brak nowych zmian do zapisania'; }
                else {
                    delay(() => {
                        if (pending && attempt === saveAttempt) { pending = false; queued = false; fail('Zapis nie został jeszcze potwierdzony. Spróbuj ponownie; dokument pozostaje w edytorze.', true); }
                    }, 30000);
                }
                await poll();
            } catch (reason) {
                pending = false;
                queued = false;
                if (!life.signal.aborted) fail(reason.message || 'Nie udało się zapisać. Spróbuj ponownie.', true);
            } finally { requesting = false; saveQueued(); }
        }
        retry.addEventListener('click', persist);
        const config = JSON.parse(document.getElementById('office-editor-config').textContent);
        config.events = {
            onAppReady() { if (!life.signal.aborted) status.textContent = 'Ładowanie dokumentu…'; },
            onDocumentReady() { if (life.signal.aborted) return; status.textContent = 'Dokument otwarty'; clearInterval(pollTimer); pollTimer = setInterval(poll, 4000); },
            onDocumentStateChange(event) {
                if (life.signal.aborted || sessionInvalid) return;
                if (event.data) { editGeneration++; status.textContent = 'Zmiany w edytorze'; }
                else { clearTimeout(autoSaveTimer); autoSaveTimer = delay(persist, 1500); }
            },
            onError() { if (!life.signal.aborted) fail('Edytor zgłosił błąd. Zachowaj otwarte okno i sprawdź połączenie z serwerem edycji.'); },
            onRequestClose() { if (!life.signal.aborted) location.href = root.dataset.backUrl; },
        };
        const script = document.createElement('script');
        script.src = holder.dataset.apiUrl;
        script.onload = () => {
            if (life.signal.aborted) return;
            try { editor = new window.DocsAPI.DocEditor('office-doc-editor', config); }
            catch { fail('Nie udało się uruchomić edytora. Odśwież stronę.'); }
        };
        script.onerror = () => { if (!life.signal.aborted) { status.textContent = 'Edytor niedostępny'; fail('Nie można połączyć się z serwerem edycji. Uruchom go i odśwież stronę. Plik pozostaje zapisany w Ancore.'); } };
        document.head.append(script);
        window.addEventListener('pagehide', () => {
            life.abort();
            clearInterval(pollTimer);
            clearTimeout(autoSaveTimer);
            timeouts.forEach(clearTimeout);
            script.onload = script.onerror = null;
            script.remove();
            editor?.destroyEditor();
        }, {once: true});
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
    document.addEventListener('ancore:content-loaded', init);
})();
