(function () {
    if (window.AncoreGlobalSearch) return;
    const panel = document.querySelector('[data-global-search-panel]');
    const closeButton = document.querySelector('[data-global-search-close]');
    const backdrop = document.querySelector('[data-global-search-backdrop]');
    const form = document.querySelector('[data-global-search-form]');
    const input = document.querySelector('[data-global-search-input]');
    const clearButton = document.querySelector('[data-global-search-clear]');
    const results = document.querySelector('[data-global-search-results]');
    const status = document.querySelector('[data-global-search-status]');
    const topbar = document.querySelector('[data-app-topbar]');
    const searchUrl = panel?.dataset.searchUrl || '';
    const minimumQueryLength = 2;
    const debounceDelay = 180;
    let requestController = null;
    let debounceTimer = null;
    let restoreFocusTo = null;
    let activeResultIndex = -1;
    let inertElements = [];

    if (!panel || !input || !results || !searchUrl) return;

    function iconNode(iconName) {
        const icon = document.createElement('i');
        icon.setAttribute('data-icon', iconName || 'search');
        icon.setAttribute('aria-hidden', 'true');
        return icon;
    }

    function renderIcons(scope) {
        window.AncoreIcons?.render(scope);
    }

    function stateElement(kind, icon, title, copy) {
        const state = document.createElement('div');
        state.className = `global-search-state global-search-state--${kind}`;

        const visual = document.createElement('span');
        visual.className = 'global-search-state__icon';
        visual.setAttribute('aria-hidden', 'true');
        visual.appendChild(iconNode(icon));

        const heading = document.createElement('h3');
        heading.textContent = title;
        const description = document.createElement('p');
        description.textContent = copy;
        state.append(visual, heading, description);
        return state;
    }

    function renderWelcome() {
        results.replaceChildren(stateElement(
            'welcome',
            'scan-search',
            'Zacznij od nazwy lub słowa kluczowego',
            'Wpisz co najmniej 2 znaki. Przeszukamy cały bieżący Workspace.'
        ));
        activeResultIndex = -1;
        status.textContent = '';
        renderIcons(results);
    }

    function renderPrompt(query) {
        results.replaceChildren(stateElement(
            'prompt',
            'text-cursor-input',
            'Wpisz jeszcze jeden znak',
            `Fraza „${query}” jest zbyt krótka, aby rozpocząć globalne wyszukiwanie.`
        ));
        activeResultIndex = -1;
        status.textContent = 'Wpisz co najmniej 2 znaki.';
        renderIcons(results);
    }

    function renderLoading() {
        const loading = document.createElement('div');
        loading.className = 'global-search-loading';
        loading.setAttribute('aria-hidden', 'true');
        for (let index = 0; index < 6; index += 1) {
            const row = document.createElement('span');
            row.className = 'global-search-loading__row';
            row.innerHTML = '<span></span><span></span>';
            loading.appendChild(row);
        }
        results.replaceChildren(loading);
        activeResultIndex = -1;
        status.textContent = 'Wyszukiwanie…';
    }

    function renderEmpty(query) {
        results.replaceChildren(stateElement(
            'empty',
            'search-x',
            'Nie znaleźliśmy wyników',
            `Sprawdź pisownię „${query}” albo użyj krótszej, bardziej ogólnej frazy.`
        ));
        activeResultIndex = -1;
        status.textContent = `Brak wyników dla frazy ${query}.`;
        renderIcons(results);
    }

    function renderError() {
        const errorState = stateElement(
            'error',
            'wifi-off',
            'Nie udało się pobrać wyników',
            'Sprawdź połączenie i spróbuj ponownie za chwilę.'
        );
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.className = 'global-search-state__retry';
        retry.textContent = 'Spróbuj ponownie';
        retry.addEventListener('click', function () {
            runSearch(input.value.trim());
        });
        errorState.appendChild(retry);
        results.replaceChildren(errorState);
        activeResultIndex = -1;
        status.textContent = 'Wystąpił błąd wyszukiwania.';
        renderIcons(results);
    }

    function createResult(result, resultIndex) {
        const link = document.createElement('a');
        link.className = 'global-search-result';
        link.href = result.url;
        if (result.new_tab) {
            link.target = '_blank';
            link.rel = 'noopener';
        }
        link.dataset.globalSearchResult = '';
        link.dataset.resultIndex = String(resultIndex);

        if (result.icon) {
            const visual = document.createElement('span');
            visual.className = 'global-search-result__icon';
            visual.setAttribute('aria-hidden', 'true');
            visual.appendChild(iconNode(result.icon));
            link.appendChild(visual);
        }

        const body = document.createElement('span');
        body.className = 'global-search-result__body';
        const titleLine = document.createElement('span');
        titleLine.className = 'global-search-result__title-line';
        const title = document.createElement('strong');
        title.className = 'global-search-result__title';
        title.textContent = result.title;
        const type = document.createElement('span');
        type.className = 'global-search-result__type';
        type.textContent = result.type;
        titleLine.append(title, type);
        body.appendChild(titleLine);

        if (result.meta) {
            const meta = document.createElement('span');
            meta.className = 'global-search-result__meta';
            meta.textContent = result.meta;
            body.appendChild(meta);
        }

        if (result.eyebrow) {
            const eyebrow = document.createElement('span');
            eyebrow.className = 'global-search-result__eyebrow';
            eyebrow.textContent = result.eyebrow;
            body.appendChild(eyebrow);
        }

        const arrow = document.createElement('span');
        arrow.className = 'global-search-result__arrow';
        arrow.setAttribute('aria-hidden', 'true');
        arrow.appendChild(iconNode('arrow-up-right'));
        link.append(body, arrow);
        return link;
    }

    function renderSearchResults(payload) {
        if (!payload.groups?.length || payload.total === 0) {
            renderEmpty(payload.query || input.value.trim());
            return;
        }

        const fragment = document.createDocumentFragment();
        let resultIndex = 0;
        payload.groups.forEach(function (group) {
            const section = document.createElement('section');
            section.className = 'global-search-group';

            const header = document.createElement('header');
            header.className = 'global-search-group__header';
            const heading = document.createElement('h3');
            heading.append(iconNode(group.icon));
            const label = document.createElement('span');
            label.textContent = group.label;
            heading.appendChild(label);
            const count = document.createElement('span');
            count.className = 'global-search-group__count';
            count.textContent = group.has_more ? `${group.results.length}+` : String(group.results.length);
            header.append(heading, count);
            section.appendChild(header);

            const list = document.createElement('div');
            list.className = 'global-search-group__list';
            group.results.forEach(function (item) {
                list.appendChild(createResult(item, resultIndex));
                resultIndex += 1;
            });
            section.appendChild(list);
            fragment.appendChild(section);
        });

        if (payload.truncated) {
            const note = document.createElement('p');
            note.className = 'global-search-results__limit-note';
            note.textContent = 'Pokazujemy najtrafniejsze wyniki. Doprecyzuj frazę, aby zawęzić listę.';
            fragment.appendChild(note);
        }

        results.replaceChildren(fragment);
        activeResultIndex = -1;
        status.textContent = payload.truncated
            ? `Pokazano ${payload.total} wyników. Doprecyzuj frazę, aby zawęzić listę.`
            : `Znaleziono ${payload.total} wyników.`;
        renderIcons(results);
    }

    async function runSearch(query) {
        window.clearTimeout(debounceTimer);
        requestController?.abort();

        if (!query) {
            renderWelcome();
            return;
        }
        if (query.length < minimumQueryLength) {
            renderPrompt(query);
            return;
        }

        requestController = new AbortController();
        const controller = requestController;
        renderLoading();

        try {
            const url = new URL(searchUrl, window.location.origin);
            url.searchParams.set('q', query);
            const response = await fetch(url, {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(`Search failed with ${response.status}`);
            const payload = await response.json();
            if (controller !== requestController || input.value.trim() !== query) return;
            renderSearchResults(payload);
        } catch (error) {
            if (error.name !== 'AbortError') renderError();
        }
    }

    function queueSearch() {
        const query = input.value.trim();
        clearButton.hidden = !input.value;
        window.clearTimeout(debounceTimer);
        requestController?.abort();
        if (!query || query.length < minimumQueryLength) {
            runSearch(query);
            return;
        }
        debounceTimer = window.setTimeout(function () {
            runSearch(query);
        }, debounceDelay);
    }

    function setActiveResult(nextIndex) {
        const items = Array.from(results.querySelectorAll('[data-global-search-result]'));
        if (!items.length) return;
        activeResultIndex = (nextIndex + items.length) % items.length;
        items.forEach(function (item, index) {
            const active = index === activeResultIndex;
            item.classList.toggle('is-active', active);
            item.setAttribute('aria-current', active ? 'true' : 'false');
        });
        items[activeResultIndex].scrollIntoView({ block: 'nearest' });
    }

    function openSelectedResult() {
        const active = results.querySelector('.global-search-result.is-active')
            || results.querySelector('[data-global-search-result]');
        if (!active) return false;
        active.click();
        return true;
    }

    function isOpen() {
        return !panel.hidden;
    }

    function setOpen(open, options = {}) {
        if (open === isOpen()) {
            if (open && options.focus !== false) input.focus({ preventScroll: true });
            return;
        }

        input.setAttribute('aria-expanded', String(open));
        document.body.classList.toggle('global-search-open', open);
        panel.hidden = !open;
        backdrop.hidden = !open;

        if (open) {
            restoreFocusTo = document.activeElement.closest('.global-search-panel') ? input : document.activeElement;
            window.dispatchEvent(new CustomEvent('ancore:global-search-open'));
            const background = Array.from(document.querySelectorAll('main.main-content, .sidebar'));
            inertElements = background.filter(element => element instanceof HTMLElement && !element.inert);
            inertElements.forEach(element => { element.inert = true; });
            if (options.focus !== false) {
                input.focus({ preventScroll: true });
                input.select();
            }
            if (options.search !== false) queueSearch();
        } else {
            window.clearTimeout(debounceTimer);
            requestController?.abort();
            inertElements.forEach(element => { element.inert = false; });
            inertElements = [];
            if (options.restoreFocus !== false) restoreFocusTo?.focus?.({ preventScroll: true });
            restoreFocusTo = null;
        }
    }

    input.addEventListener('click', function () {
        setOpen(true, { focus: false });
    });
    closeButton?.addEventListener('click', function () {
        setOpen(false);
    });
    backdrop?.addEventListener('click', function () {
        setOpen(false);
    });
    form?.addEventListener('submit', function (event) {
        event.preventDefault();
        openSelectedResult();
    });
    input.addEventListener('input', function () {
        setOpen(true, { focus: false, search: false });
        queueSearch();
    });
    input.addEventListener('keydown', function (event) {
        if (!isOpen() && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
            event.preventDefault();
            setOpen(true);
            return;
        }
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            setActiveResult(activeResultIndex + 1);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            setActiveResult(activeResultIndex - 1);
        } else if (event.key === 'Enter') {
            event.preventDefault();
            openSelectedResult();
        }
    });
    clearButton?.addEventListener('click', function () {
        setOpen(true, { focus: false, search: false });
        input.value = '';
        clearButton.hidden = true;
        runSearch('');
        input.focus({ preventScroll: true });
    });
    results.addEventListener('mousemove', function (event) {
        const item = event.target.closest('[data-global-search-result]');
        if (!item) return;
        setActiveResult(Number(item.dataset.resultIndex));
    });
    results.addEventListener('click', function (event) {
        if (event.target.closest('[data-global-search-result]')) setOpen(false);
    });
    window.addEventListener('ancore:notifications-open', function () {
        setOpen(false, { restoreFocus: false });
    });
    window.addEventListener('ancore:workspace-menu-open', function () {
        setOpen(false, { restoreFocus: false });
    });
    window.addEventListener('ancore:sidebar-toggle', function () {
        setOpen(false, { restoreFocus: false });
    });
    document.addEventListener('ancore:content-unloading', function () {
        setOpen(false, { restoreFocus: false });
    });

    document.addEventListener('keydown', function (event) {
        if (document.querySelector('.confirm-modal-overlay')) return;
        const target = event.target;
        const typing = target instanceof HTMLElement
            && (target.matches('input, textarea, select') || target.isContentEditable);
        if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase('pl') === 'k') {
            event.preventDefault();
            setOpen(true);
            return;
        }
        if (event.key === 'Tab' && isOpen()) {
            const selector = 'button:not(:disabled), input:not(:disabled), a[href]';
            const focusable = [...(topbar?.querySelectorAll(selector) || []), ...panel.querySelectorAll(selector)]
                .filter(element => {
                    const rect = element.getBoundingClientRect();
                    return element.getClientRects().length && getComputedStyle(element).visibility !== 'hidden'
                        && !element.closest('[inert]') && rect.right > 0 && rect.left < innerWidth;
                });
            if (focusable.length) {
                const index = focusable.indexOf(document.activeElement);
                const next = index < 0 ? (event.shiftKey ? focusable.length - 1 : 0)
                    : (index + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length;
                event.preventDefault();
                focusable[next].focus();
            }
            return;
        }
        if (event.key === 'Escape' && isOpen()) {
            event.preventDefault();
            setOpen(false);
        } else if (!typing && event.key === '/' && !isOpen()) {
            event.preventDefault();
            setOpen(true);
        }
    });
    window.AncoreGlobalSearch = { close: () => setOpen(false) };
})();
