window.EXCALIDRAW_ASSET_PATH = document.getElementById('board-root').dataset.assets;
import('./board.jsx').catch(() => {
    document.getElementById('board-root').textContent = 'Nie udało się załadować tablicy. Odśwież stronę.';
});
