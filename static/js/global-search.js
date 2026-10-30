(function () {
    if (window.AncoreGlobalSearch) return;
    const panel = document.querySelector('[data-global-search-panel]');
    const form = document.querySelector('[data-global-search-form]');
    const input = document.querySelector('[data-global-search-input]');
    const clearButton = document.querySelector('[data-global-search-clear]');
    const closeButton = document.querySelector('[data-global-search-close]');
    const results = document.querySelector('[data-global-search-results]');
    const status = document.querySelector('[data-global-search-status]');
    const filters = document.querySelector('[data-global-search-filters]');
    const recentHeading = document.querySelector('[data-global-search-heading]');
    const summary = document.querySelector('[data-global-search-summary]');
    const searchUrl = panel?.dataset.searchUrl || '';
    const minimumQueryLength = 2;
    const debounceDelay = 180;
    const searchFilters = [
        { key: 'all', label: 'Wszystko' },
        { key: 'space_tasks', label: 'Zadania' },
        { key: 'spaces', label: 'Przestrzenie' },
        { key: 'office-documents', label: 'Dokumenty' },
        { key: 'documents', label: 'Pliki' },
        { key: 'tags', label: 'Tagi' },
        { key: 'calendar', label: 'Kalendarz' },
        { key: 'resources', label: 'Zasoby' },
        { key: 'document-libraries', label: 'Dyski' },
        { key: 'document-folders', label: 'Foldery' },
        { key: 'workplaces', label: 'Workspace' },
        { key: 'navigation', label: 'Nawigacja' },
    ];
    let requestController = null;
    let debounceTimer = null;
    let suppressFocusOpen = false;
    let currentPayload = null;
    let selectedGroup = 'all';
    let activeResultIndex = -1;

    if (!panel || !form || !input || !results || !filters || !searchUrl) return;

    const shortcut = form.querySelector('.global-search-form__shortcut');
    if (shortcut) shortcut.textContent = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘ K' : 'Ctrl K';

    function iconNode(iconName) {
        const icon = document.createElement('i');
        icon.setAttribute('data-icon', iconName || 'search');
        icon.setAttribute('aria-hidden', 'true');
        return icon;
    }

    function renderIcons(scope) {
        window.AncoreIcons?.render(scope);
    }

    function matchedText(text, query) {
        const fragment = document.createDocumentFragment();
        const term = query.trim().toLocaleLowerCase('pl');
        if (term.length < minimumQueryLength) {
            fragment.append(text);
            return fragment;
        }
        const lower = text.toLocaleLowerCase('pl');
        let start = 0;
        let match = lower.indexOf(term);
        while (match !== -1) {
            fragment.append(text.slice(start, match));
            const mark = document.createElement('mark');
            mark.textContent = text.slice(match, match + term.length);
            fragment.appendChild(mark);
            start = match + term.length;
            match = lower.indexOf(term, start);
        }
        fragment.append(text.slice(start));
        return fragment;
    }

    function resetActiveResult() {
        activeResultIndex = -1;
        results.querySelectorAll('.global-search-result.is-active').forEach(item => item.classList.remove('is-active'));
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
            'Znajdź zadanie, przestrzeń lub dokument',
            'Wpisz co najmniej 2 znaki. Ostatnio oglądane elementy pojawią się tutaj, gdy je otworzysz.'
        ));
        activeResultIndex = -1;
        status.textContent = 'Brak ostatnio oglądanych elementów.';
        summary.textContent = 'Ostatnio oglądane w tym Workspace';
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
        summary.textContent = status.textContent;
        renderIcons(results);
    }

    function renderLoading() {
        const loading = document.createElement('div');
        loading.className = 'global-search-loading';
        loading.setAttribute('aria-hidden', 'true');
        for (let index = 0; index < 6; index += 1) {
            const row = document.createElement('span');
            row.className = 'global-search-loading__row';
            row.append(document.createElement('span'), document.createElement('span'));
            loading.appendChild(row);
        }
        results.replaceChildren(loading);
        activeResultIndex = -1;
        status.textContent = 'Wyszukiwanie…';
        summary.textContent = status.textContent;
    }

    function renderEmpty(query) {
        const emptyState = stateElement(
            'empty',
            'search-x',
            'Nie znaleźliśmy wyników',
            `Sprawdź pisownię „${query}” albo użyj krótszej, bardziej ogólnej frazy.`
        );
        if (selectedGroup !== 'all') {
            const all = document.createElement('button');
            all.type = 'button';
            all.className = 'global-search-state__retry';
            all.textContent = 'Szukaj we wszystkich typach';
            all.addEventListener('click', function () {
                selectedGroup = 'all';
                renderFilters(currentPayload);
                if (currentPayload) renderSearchResults(currentPayload);
                focusInput();
            });
            emptyState.appendChild(all);
        }
        results.replaceChildren(emptyState);
        activeResultIndex = -1;
        status.textContent = `Brak wyników dla frazy ${query}.`;
        summary.textContent = 'Wyniki: 0';
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
            focusInput();
            runSearch(input.value.trim());
        });
        errorState.appendChild(retry);
        results.replaceChildren(errorState);
        activeResultIndex = -1;
        status.textContent = 'Wystąpił błąd wyszukiwania.';
        summary.textContent = 'Spróbuj ponownie';
        renderIcons(results);
    }

    function createResult(result, resultIndex, groupIcon) {
        const link = document.createElement('a');
        link.className = 'global-search-result';
        link.href = result.url;
        if (result.new_tab) {
            link.target = '_blank';
            link.rel = 'noopener';
        }
        link.dataset.globalSearchResult = '';
        link.dataset.resultIndex = String(resultIndex);

        if (result.avatar) {
            const avatar = result.avatar;
            const visual = document.createElement('span');
            visual.className = `profile-avatar space-avatar global-search-result__avatar ${avatar.color_class || ''} ${avatar.photo_url ? 'has-photo' : `space-avatar-art ${avatar.preset_class || ''}`}`;
            visual.setAttribute('aria-hidden', 'true');
            visual.dataset.spaceAvatar = '';
            if (avatar.background_color) visual.style.setProperty('--profile-avatar-bg', avatar.background_color);
            if (avatar.foreground_color) visual.style.setProperty('--profile-avatar-fg', avatar.foreground_color);
            if (avatar.photo_url) {
                const photo = document.createElement('img');
                photo.src = avatar.photo_url;
                photo.alt = '';
                photo.draggable = false;
                visual.appendChild(photo);
            }
            link.appendChild(visual);
        } else if (result.icon || groupIcon) {
            const visual = document.createElement('span');
            visual.className = 'global-search-result__icon' + (['Zadanie', 'Podzadanie'].includes(result.type) ? ' tasks-issue-type' : '');
            visual.setAttribute('aria-hidden', 'true');
            visual.appendChild(iconNode(result.icon || groupIcon));
            link.appendChild(visual);
        }

        const body = document.createElement('span');
        body.className = 'global-search-result__body';
        const titleLine = document.createElement('span');
        titleLine.className = 'global-search-result__title-line';
        const title = document.createElement('strong');
        title.className = 'global-search-result__title';
        title.appendChild(matchedText(result.title, input.value));
        title.title = result.title;
        const type = document.createElement('span');
        type.className = 'global-search-result__type';
        type.textContent = result.type;
        titleLine.append(title, type);
        body.appendChild(titleLine);

        if (result.meta) {
            const meta = document.createElement('span');
            meta.className = 'global-search-result__meta';
            meta.appendChild(matchedText(result.meta, input.value));
            meta.title = result.meta;
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

    function renderFilters(payload) {
        const recent = !input.value.trim();
        filters.hidden = recent;
        if (recentHeading) {
            recentHeading.hidden = !recent;
            recentHeading.replaceChildren(iconNode('clock'), document.createTextNode('Ostatnio oglądane'));
            if (payload?.recent) {
                const count = document.createElement('span');
                count.className = 'global-search-filter-count';
                count.textContent = String(payload.total);
                recentHeading.appendChild(count);
            }
            renderIcons(recentHeading);
        }
        const groups = payload?.groups || [];
        const fragment = document.createDocumentFragment();
        searchFilters.filter((group, index) => index < 5 || group.key === selectedGroup || groups.some(result => result.key === group.key)).forEach(group => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'tasks-filter-button';
            button.dataset.searchGroup = group.key;
            button.setAttribute('aria-pressed', String(group.key === selectedGroup));
            button.textContent = group.label;
            if (payload) {
                const resultGroup = groups.find(result => result.key === group.key);
                const count = document.createElement('span');
                count.className = 'global-search-filter-count';
                const total = group.key === 'all' ? payload.total : resultGroup?.results.length || 0;
                const hasMore = group.key === 'all' ? payload.truncated : resultGroup?.has_more;
                count.textContent = `${total}${hasMore ? '+' : ''}`;
                button.appendChild(count);
            }
            fragment.appendChild(button);
        });
        filters.replaceChildren(fragment);
    }

    function renderSearchResults(payload) {
        const groups = (payload.groups || []).filter(group => payload.recent || selectedGroup === 'all' || group.key === selectedGroup);
        const total = groups.reduce((count, group) => count + group.results.length, 0);
        if (!total) {
            if (payload.recent) renderWelcome();
            else renderEmpty(payload.query || input.value.trim());
            return;
        }

        const fragment = document.createDocumentFragment();
        let resultIndex = 0;
        groups.forEach(function (group) {
            const section = document.createElement('section');
            section.className = 'global-search-group';

            if (!payload.recent) {
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
            }

            const list = document.createElement('div');
            list.className = 'global-search-group__list';
            group.results.forEach(function (item) {
                list.appendChild(createResult(item, resultIndex, group.icon));
                resultIndex += 1;
            });
            section.appendChild(list);
            fragment.appendChild(section);
        });

        const truncated = groups.some(group => group.has_more);
        if (truncated) {
            const note = document.createElement('p');
            note.className = 'global-search-results__limit-note';
            note.textContent = 'Pokazujemy najtrafniejsze wyniki. Doprecyzuj frazę, aby zawęzić listę.';
            fragment.appendChild(note);
        }

        results.replaceChildren(fragment);
        activeResultIndex = -1;
        status.textContent = payload.recent ? `Ostatnio oglądane: ${total}.` : truncated
            ? `Pokazano ${total} wyników. Doprecyzuj frazę, aby zawęzić listę.`
            : `Znaleziono ${total} wyników.`;
        summary.textContent = payload.recent ? 'Ostatnio oglądane w tym Workspace'
            : `Wyniki: ${total}${truncated ? '+' : ''}`;
        renderIcons(results);
    }

    async function runSearch(query) {
        window.clearTimeout(debounceTimer);
        requestController?.abort();

        requestController = null;
        currentPayload = null;
        renderFilters(null);
        if (query && query.length < minimumQueryLength) {
            results.setAttribute('aria-busy', 'false');
            renderPrompt(query);
            return;
        }

        requestController = new AbortController();
        const controller = requestController;
        results.setAttribute('aria-busy', 'true');
        renderLoading();

        try {
            const url = new URL(searchUrl, window.location.origin);
            url.searchParams.set('q', query);
            if (!query) url.searchParams.set('recent', '1');
            const response = await fetch(url, {
                credentials: 'same-origin',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error(`Search failed with ${response.status}`);
            const payload = await response.json();
            if (controller.signal.aborted || controller !== requestController || !isOpen() || input.value.trim() !== query) return;
            currentPayload = payload;
            results.setAttribute('aria-busy', 'false');
            renderFilters(payload);
            renderSearchResults(payload);
        } catch (error) {
            if (error.name !== 'AbortError' && controller === requestController && !controller.signal.aborted && isOpen()) {
                results.setAttribute('aria-busy', 'false');
                renderError();
            }
        }
    }

    function queueSearch() {
        const query = input.value.trim();
        clearButton.hidden = !input.value;
        window.clearTimeout(debounceTimer);
        requestController?.abort();
        requestController = null;
        currentPayload = null;
        if (!query) selectedGroup = 'all';
        renderFilters(null);
        if (!query || query.length < minimumQueryLength) {
            runSearch(query);
            return;
        }
        results.setAttribute('aria-busy', 'true');
        renderLoading();
        debounceTimer = window.setTimeout(function () {
            runSearch(query);
        }, debounceDelay);
    }

    function setActiveResult(nextIndex, focus = false) {
        const items = Array.from(results.querySelectorAll('[data-global-search-result]'));
        if (!items.length) return;
        activeResultIndex = (nextIndex + items.length) % items.length;
        items.forEach(function (item, index) {
            const active = index === activeResultIndex;
            item.classList.toggle('is-active', active);
        });
        if (focus) {
            items[activeResultIndex].focus({ preventScroll: true });
            items[activeResultIndex].scrollIntoView({ block: 'nearest' });
        }
    }

    function openSelectedResult() {
        if (!isOpen() || !currentPayload || currentPayload.query !== input.value.trim() || results.getAttribute('aria-busy') === 'true') return false;
        const active = results.querySelector('.global-search-result.is-active')
            || results.querySelector('[data-global-search-result]');
        if (!active) return false;
        active.click();
        return true;
    }

    function isOpen() {
        return !panel.hidden;
    }

    function focusInput(select = false) {
        resetActiveResult();
        suppressFocusOpen = true;
        input.focus({ preventScroll: true });
        if (select) input.select();
        suppressFocusOpen = false;
    }

    function setOpen(open, options = {}) {
        if (open === isOpen()) {
            if (open && options.focus !== false) focusInput(true);
            return;
        }
        input.setAttribute('aria-expanded', String(open));
        document.body.classList.toggle('global-search-open', open);
        panel.hidden = !open;
        if (open) {
            window.dispatchEvent(new CustomEvent('ancore:global-search-open'));
            if (options.focus !== false) focusInput(true);
            if (options.search !== false) queueSearch();
        } else {
            resetActiveResult();
            window.clearTimeout(debounceTimer);
            requestController?.abort();
            requestController = null;
            if (options.restoreFocus !== false) focusInput();
        }
    }

    input.addEventListener('focus', function () {
        resetActiveResult();
        if (!suppressFocusOpen) setOpen(true, { focus: false });
    });
    input.addEventListener('click', function () {
        setOpen(true, { focus: false });
    });
    form?.addEventListener('submit', function (event) {
        event.preventDefault();
        if (!isOpen()) {
            setOpen(true);
            return;
        }
        openSelectedResult();
    });
    input.addEventListener('input', function () {
        setOpen(true, { focus: false, search: false });
        queueSearch();
    });
    input.addEventListener('keydown', function (event) {
        if (event.isComposing) return;
        if (!isOpen() && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
            event.preventDefault();
            setOpen(true);
            return;
        }
        if (event.key === 'ArrowDown') {
            event.preventDefault();
            setActiveResult(0, true);
        } else if (event.key === 'ArrowUp') {
            event.preventDefault();
            setActiveResult(-1, true);
        } else if (event.key === 'Enter') {
            event.preventDefault();
            openSelectedResult();
        }
    });
    clearButton?.addEventListener('click', function () {
        setOpen(true, { focus: false, search: false });
        input.value = '';
        clearButton.hidden = true;
        queueSearch();
        focusInput();
    });
    closeButton?.addEventListener('click', function () {
        setOpen(false);
    });
    results.addEventListener('click', function (event) {
        if (event.target.closest('[data-global-search-result]')) setOpen(false, { restoreFocus: false });
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
        input.value = '';
        clearButton.hidden = true;
        currentPayload = null;
        selectedGroup = 'all';
        renderFilters(null);
    });

    document.addEventListener('keydown', function (event) {
        if (event.defaultPrevented || event.isComposing || document.querySelector('.confirm-modal-overlay')) return;
        const target = event.target;
        const typing = target instanceof HTMLElement
            && (target.matches('input, textarea, select') || target.isContentEditable);
        if ((event.metaKey || event.ctrlKey) && event.key.toLocaleLowerCase('pl') === 'k') {
            if (form.closest('[inert]')) {
                const inbox = document.getElementById('notifications-panel');
                if (!inbox || inbox.getAttribute('aria-busy') === 'true') return;
            }
            event.preventDefault();
            setOpen(true);
            return;
        }
        if (event.key === 'Escape' && isOpen()) {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
        } else if (!typing && event.key === '/' && !isOpen()) {
            event.preventDefault();
            setOpen(true);
        }
    });
    results.addEventListener('focusin', function (event) {
        const item = event.target.closest('[data-global-search-result]');
        if (item) setActiveResult(Number(item.dataset.resultIndex));
    });
    results.addEventListener('keydown', function (event) {
        if (!event.target.closest('[data-global-search-result]') || event.isComposing) return;
        if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
        event.preventDefault();
        if (event.key === 'ArrowUp' && activeResultIndex === 0) focusInput();
        else setActiveResult(event.key === 'Home' ? 0 : event.key === 'End' ? -1
            : activeResultIndex + (event.key === 'ArrowDown' ? 1 : -1), true);
    });
    filters.addEventListener('click', function (event) {
        const button = event.target.closest('[data-search-group]');
        if (!button) return;
        selectedGroup = button.dataset.searchGroup;
        filters.querySelectorAll('button').forEach(item => {
            item.setAttribute('aria-pressed', String(item === button));
        });
        resetActiveResult();
        if (currentPayload) renderSearchResults(currentPayload);
        results.scrollTop = 0;
    });
    document.addEventListener('pointerdown', function (event) {
        if (isOpen() && !form.contains(event.target)) setOpen(false, { restoreFocus: false });
    });
    document.addEventListener('focusin', function (event) {
        if (isOpen() && !form.contains(event.target)) setOpen(false, { restoreFocus: false });
    });
    document.addEventListener('ancore:content-loaded', function () {
        setOpen(false, { restoreFocus: false });
        input.value = '';
        clearButton.hidden = true;
        currentPayload = null;
        selectedGroup = 'all';
        renderFilters(null);
    });
    renderFilters(null);
    window.AncoreGlobalSearch = { close: () => setOpen(false, { restoreFocus: false }) };
})();
