import React from 'react';
import { createRoot } from 'react-dom/client';
import { Excalidraw, MainMenu } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import './board.css';

const root = document.getElementById('board-root');
window.EXCALIDRAW_ASSET_PATH = root.dataset.assets;
const config = JSON.parse(document.getElementById('board-config').textContent);
const initialData = {...config.scene, scrollToContent: true};
const csrf = document.querySelector('[name=csrfmiddlewaretoken]').value;
let revision = config.revision, latest = config.scene, signature = null;
let latestJSON = '', savedJSON = '', timer, inFlight = false, conflict = false;
const notify = (type, message, dirty = false) => parent.postMessage({ source: 'ancore-board', type, message, dirty }, location.origin);
const sceneJSON = () => JSON.stringify(latest);
function onChange(elements, state, files) {
    const nextSignature = elements.map(item => `${item.id}:${item.version}:${item.versionNonce}`).join('|') + state.viewBackgroundColor + Object.keys(files).join('|');
    if (nextSignature === signature) return;
    const first = signature === null;
    if (config.readOnly && !first) return;
    signature = nextSignature;
    latest = { type: 'excalidraw', version: 2, source: 'Ancore', elements,
        appState: { viewBackgroundColor: state.viewBackgroundColor }, files };
    if (first) {
        savedJSON = latestJSON = sceneJSON();
        notify('status', 'Tablica otwarta');
        return;
    }
    notify('status', 'Niezapisane zmiany', true);
    clearTimeout(timer);
    timer = setTimeout(() => { latestJSON = sceneJSON(); persist(); }, 1200);
}
async function persist() {
    if (config.readOnly) return;
    latestJSON = sceneJSON();
    if (inFlight || conflict) return;
    if (latestJSON === savedJSON) { notify('status', 'Wszystkie zmiany zapisane'); return; }
    const sending = latestJSON;
    inFlight = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 20000);
    notify('status', 'Zapisywanie tablicy…', true);
    try {
        const response = await fetch(config.saveUrl, { method: 'POST', signal: controller.signal, headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
            body: JSON.stringify({revision, scene: JSON.parse(sending)}) });
        if (response.status === 409) conflict = true;
        if (response.redirected) throw new Error('Sesja wygasła. Pobierz kopię tablicy i zaloguj się ponownie.');
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Zapis nie powiódł się. Pobierz kopię tablicy i spróbuj ponownie.');
        revision = result.revision;
        savedJSON = sending;
        latestJSON = sceneJSON();
        const dirty = latestJSON !== savedJSON;
        notify('status', dirty ? 'Nowsze zmiany oczekują na zapis' : `Zapisano w Ancore ${result.saved_at}`, dirty);
        if (dirty) { clearTimeout(timer); timer = setTimeout(persist, 600); }
    } catch (error) {
        notify('error', error.message || 'Nie udało się zapisać tablicy. Sprawdź połączenie.', true);
    } finally { clearTimeout(timeout); inFlight = false; }
}
function downloadCopy() {
    const url = URL.createObjectURL(new Blob([sceneJSON()], {type: 'application/json'}));
    const link = document.createElement('a');
    link.href = url; link.download = `${config.name}.excalidraw`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 5000);
}
window.addEventListener('message', event => {
    if (event.origin === location.origin && event.source === parent && event.data?.source === 'ancore' && ['save', 'download'].includes(event.data.type)) {
        if (event.data.type === 'download') { downloadCopy(); return; }
        if (conflict) notify('error', 'Najpierw pobierz kopię tablicy z menu. Następnie otwórz aktualną wersję w nowej karcie.', true);
        else persist();
    }
});
window.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault(); event.stopPropagation(); persist();
    }
}, true);
window.addEventListener('beforeunload', event => {
    if (signature !== null && sceneJSON() !== savedJSON) { event.preventDefault(); event.returnValue = ''; }
});
function Board() {
    return <Excalidraw initialData={initialData} onChange={onChange} langCode="pl-PL" name={config.name} viewModeEnabled={!!config.readOnly}
        autoFocus validateEmbeddable={false} UIOptions={{canvasActions: {export: {saveFileToDisk: true}}}}
        onLinkOpen={(element, event) => { if (!/^(https?:\/\/|mailto:)/i.test(element.link || '')) event.preventDefault(); }}>
        <MainMenu>
            <MainMenu.Item onSelect={persist}>Zapisz w Ancore</MainMenu.Item>
            <MainMenu.Item onSelect={downloadCopy}>Pobierz kopię tablicy</MainMenu.Item>
            <MainMenu.DefaultItems.LoadScene />
            <MainMenu.DefaultItems.SaveAsImage />
            <MainMenu.Separator />
            <MainMenu.DefaultItems.SearchMenu />
            <MainMenu.DefaultItems.CommandPalette />
            <MainMenu.DefaultItems.ClearCanvas />
            <MainMenu.DefaultItems.ChangeCanvasBackground />
            <MainMenu.DefaultItems.ToggleTheme />
            <MainMenu.DefaultItems.Help />
        </MainMenu>
    </Excalidraw>;
}
createRoot(root).render(<Board />);
