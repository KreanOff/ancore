(() => {
    function init() {
        const root = document.querySelector('[data-office-suite]');
        if (!root || root.dataset.initialized) return;
        root.dataset.initialized = 'true';
        const status = root.querySelector('[data-suite-status]');
        const error = root.querySelector('[data-suite-error]');
        const save = root.querySelector('[data-suite-save]');
        const csrf = root.querySelector('[name=csrfmiddlewaretoken]').value;
        const frame = root.querySelector('[data-board-frame]');
        let revision = Number(root.dataset.revision), pending = false, boardDirty = false;
        function fail(message) { error.textContent = message; error.hidden = false; }
        function clearError() { error.hidden = true; }
        if (frame) {
            window.addEventListener('message', event => {
                if (event.origin !== location.origin || event.source !== frame.contentWindow || event.data?.source !== 'ancore-board') return;
                const data = event.data;
                if (data.type === 'status') {
                    status.textContent = data.message;
                    boardDirty = data.dirty;
                    save.disabled = false;
                    if (!data.dirty) clearError();
                } else if (data.type === 'error') {
                    fail(data.message);
                    save.disabled = false;
                }
            });
            root.querySelector('[data-suite-download]').addEventListener('click', event => {
                if (save.disabled) return;
                event.preventDefault();
                frame.contentWindow.postMessage({source: 'ancore', type: 'download'}, location.origin);
            });
            save.addEventListener('click', () => frame.contentWindow.postMessage({source: 'ancore', type: 'save'}, location.origin));
            window.addEventListener('beforeunload', event => {
                if (boardDirty) { event.preventDefault(); event.returnValue = ''; }
            });
            setTimeout(() => { if (save.disabled) fail('Nie udało się załadować tablicy. Odśwież stronę i sprawdź połączenie.'); }, 20000);
            return;
        }
        const holder = root.querySelector('[data-api-url]');
        if (!holder) { status.textContent = 'Dokument zapisany'; return; }
        let editor, pollTimer, autoSaveTimer, editGeneration = 0, savingGeneration = 0, saveAttempt = 0, sessionInvalid = false;
        async function poll() {
            try {
                const response = await fetch(root.dataset.stateUrl, {headers: {'Accept': 'application/json'}, cache: 'no-store'});
                if (!response.ok || response.redirected) throw new Error();
                const data = await response.json();
                if (data.key !== config.document.key) {
                    sessionInvalid = true;
                    pending = false;
                    save.disabled = true;
                    status.textContent = 'Sesja dokumentu zmieniła się';
                    fail('Plik został podmieniony lub sesja zakończona. Pobierz swoje zmiany z menu Plik edytora i otwórz aktualną wersję w nowej karcie.');
                    return;
                }
                if (data.save_error) fail('Nie udało się zapisać pliku w Ancore. Pozostaw edytor otwarty i spróbuj zapisać ponownie.');
                if (data.revision > revision) {
                    revision = data.revision;
                    pending = false;
                    clearError();
                    status.textContent = savingGeneration === editGeneration ? `Zapisano w Ancore ${data.saved_at}` : 'Nowsze zmiany w edytorze';
                }
            } catch { if (pending) fail('Brak potwierdzenia zapisu. Sprawdź połączenie i ponów zapis.'); }
        }
        async function persist() {
            if (pending || sessionInvalid) return;
            pending = true;
            const attempt = ++saveAttempt;
            savingGeneration = editGeneration;
            status.textContent = 'Zapisywanie w Ancore…';
            clearError();
            try {
                const response = await fetch(root.dataset.saveUrl, {method: 'POST', headers: {'X-CSRFToken': csrf, 'X-Office-Key': config.document.key, 'Accept': 'application/json'}});
                const data = await response.json();
                if (!response.ok) throw new Error(data.error);
                if (!data.pending) { pending = false; status.textContent = 'Brak nowych zmian do zapisania'; }
                else {
                    setTimeout(() => {
                        if (pending && attempt === saveAttempt) { pending = false; fail('Zapis nie został jeszcze potwierdzony. Spróbuj ponownie; dokument pozostaje w edytorze.'); }
                    }, 30000);
                }
                await poll();
            } catch (reason) { pending = false; fail(reason.message || 'Nie udało się zapisać. Spróbuj ponownie.'); }
        }
        save.addEventListener('click', persist);
        const config = JSON.parse(document.getElementById('office-editor-config').textContent);
        config.events = {
            onAppReady() { status.textContent = 'Ładowanie dokumentu…'; },
            onDocumentReady() { status.textContent = 'Dokument otwarty'; save.disabled = false; pollTimer = setInterval(poll, 4000); },
            onDocumentStateChange(event) {
                if (event.data) { editGeneration++; status.textContent = 'Zmiany w edytorze'; }
                else { clearTimeout(autoSaveTimer); autoSaveTimer = setTimeout(persist, 1500); }
            },
            onError() { fail('Edytor zgłosił błąd. Zachowaj otwarte okno i sprawdź połączenie z serwerem edycji.'); },
            onRequestClose() { location.href = root.dataset.backUrl; },
        };
        const script = document.createElement('script');
        script.src = holder.dataset.apiUrl;
        script.onload = () => {
            try { editor = new window.DocsAPI.DocEditor('office-doc-editor', config); }
            catch { fail('Nie udało się uruchomić edytora. Odśwież stronę.'); }
        };
        script.onerror = () => { status.textContent = 'Edytor niedostępny'; fail('Nie można połączyć się z serwerem edycji. Uruchom go i odśwież stronę. Plik pozostaje zapisany w Ancore.'); };
        document.head.append(script);
        window.addEventListener('pagehide', () => { clearInterval(pollTimer); clearTimeout(autoSaveTimer); editor?.destroyEditor(); }, {once: true});
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
    document.addEventListener('ancore:content-loaded', init);
})();
