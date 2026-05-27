(function () {
    const tabsEl = document.getElementById('topbar-tabs');
    const newTabButton = document.getElementById('topbar-new-tab');

    if (!tabsEl || !newTabButton) {
        return;
    }

    const tabsKey = 'ancoreTopbarTabs';
    const activeKey = 'ancoreActiveTopbarTab';
    const maxTabs = 12;

    function currentUrl() {
        return window.location.pathname + window.location.search + window.location.hash;
    }

    function normalizeTitle(value) {
        return (value || '').replace(/\s+/g, ' ').trim();
    }

    function textFrom(selector) {
        return normalizeTitle(document.querySelector(selector)?.textContent);
    }

    function inputValue(selector) {
        return normalizeTitle(document.querySelector(selector)?.value);
    }

    function selectedText(selector) {
        const select = document.querySelector(selector);
        return normalizeTitle(select?.selectedOptions?.[0]?.textContent);
    }

    function currentTitle() {
        const issueTitle = textFrom('.tasks-issue-crumb--current') || inputValue('.tasks-issue-title-field input');
        if (issueTitle) {
            return issueTitle;
        }

        const editTaskTitle = inputValue('#id_title, input[name="title"]');
        const editTaskContext = textFrom('.tasks-context-label');
        if (editTaskTitle && editTaskContext.toLowerCase().startsWith('edycja')) {
            return editTaskTitle;
        }

        const taskListTitle = textFrom('.tasks-topbar-title');
        if (taskListTitle) {
            return taskListTitle.replace(/\s*>\s*/g, ' > ');
        }

        const boardTitle = selectedText('#board-selector');
        if (boardTitle) {
            return boardTitle;
        }

        const calendarPeriod = textFrom('#cal-period-label');
        if (calendarPeriod) {
            const calendarView = textFrom('.calendar-view-btn.is-active');
            return normalizeTitle(['Kalendarz', calendarView, calendarPeriod].filter(Boolean).join(' - '));
        }

        const contextLabel = textFrom('.tasks-control-panel .tasks-context-label');
        if (contextLabel) {
            return contextLabel;
        }

        const title = normalizeTitle(document.title.replace(/\s*[-|]\s*ancore\s*$/i, ''));
        if (title && title.toLowerCase() !== 'ancore') {
            return title;
        }

        const activeNav = document.querySelector('.nav-link.active .nav-label');
        const pageHeading = document.querySelector('.page-title, h1, h2');
        return normalizeTitle(activeNav?.textContent) || normalizeTitle(pageHeading?.textContent) || 'Nowa karta';
    }

    function createTab(url, title) {
        return {
            id: 'tab-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8),
            title: title || 'Nowa karta',
            url: url || '/',
        };
    }

    function readTabs() {
        try {
            const tabs = JSON.parse(localStorage.getItem(tabsKey));
            return Array.isArray(tabs) ? tabs.filter((tab) => tab && tab.id && tab.url) : [];
        } catch (error) {
            return [];
        }
    }

    function saveTabs(tabs) {
        localStorage.setItem(tabsKey, JSON.stringify(tabs.slice(0, maxTabs)));
    }

    function setActiveTab(id) {
        sessionStorage.setItem(activeKey, id);
    }

    function getActiveTabId() {
        return sessionStorage.getItem(activeKey);
    }

    function syncCurrentTab() {
        const url = currentUrl();
        const title = currentTitle();
        let tabs = readTabs();
        let activeId = getActiveTabId();
        let activeTab = tabs.find((tab) => tab.id === activeId);

        if (!activeTab) {
            activeTab = tabs.find((tab) => tab.url === url);
        }

        if (!activeTab) {
            activeTab = createTab(url, title);
            tabs.push(activeTab);
        } else {
            activeTab.url = url;
            activeTab.title = title;
        }

        if (tabs.length > maxTabs) {
            tabs = tabs.slice(tabs.length - maxTabs);
            if (!tabs.some((tab) => tab.id === activeTab.id)) {
                tabs.push(activeTab);
            }
        }

        setActiveTab(activeTab.id);
        saveTabs(tabs);
        return { tabs, activeId: activeTab.id };
    }

    function closeIcon() {
        return [
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"',
            ' stroke-linecap="round" aria-hidden="true">',
            '<path d="M6 6l12 12"/>',
            '<path d="M18 6L6 18"/>',
            '</svg>',
        ].join('');
    }

    function render() {
        const state = syncCurrentTab();
        const fragment = document.createDocumentFragment();

        state.tabs.forEach((tab) => {
            const tabItem = document.createElement('div');
            tabItem.className = 'topbar-tab' + (tab.id === state.activeId ? ' is-active' : '');
            tabItem.title = tab.title;

            const tabButton = document.createElement('button');
            tabButton.type = 'button';
            tabButton.className = 'topbar-tab__nav';
            tabButton.setAttribute('role', 'tab');
            tabButton.setAttribute('aria-selected', tab.id === state.activeId ? 'true' : 'false');

            const label = document.createElement('span');
            label.className = 'topbar-tab__label';
            label.textContent = tab.title;
            tabButton.appendChild(label);

            const closeButton = document.createElement('button');
            closeButton.type = 'button';
            closeButton.className = 'topbar-tab__close';
            closeButton.setAttribute('aria-label', 'Zamknij kartę');
            closeButton.setAttribute('title', 'Zamknij kartę');
            closeButton.innerHTML = closeIcon();

            tabButton.addEventListener('click', (event) => {
                event.preventDefault();
                setActiveTab(tab.id);
                if (tab.url !== currentUrl()) {
                    window.location.href = tab.url;
                }
            });

            closeButton.addEventListener('click', (event) => {
                event.preventDefault();
                closeTab(tab.id);
            });

            tabItem.appendChild(tabButton);
            tabItem.appendChild(closeButton);
            fragment.appendChild(tabItem);
        });

        tabsEl.replaceChildren(fragment);
        const activeTab = tabsEl.querySelector('.topbar-tab.is-active');
        if (activeTab) {
            activeTab.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        }
    }

    function closeTab(tabId) {
        const tabs = readTabs();
        const index = tabs.findIndex((tab) => tab.id === tabId);

        if (index === -1) {
            return;
        }

        const isActive = tabId === getActiveTabId();
        const nextTabs = tabs.filter((tab) => tab.id !== tabId);
        saveTabs(nextTabs);

        if (!nextTabs.length) {
            const newTab = createTab(currentUrl(), currentTitle());
            saveTabs([newTab]);
            setActiveTab(newTab.id);
            render();
            return;
        }

        if (isActive) {
            const nextTab = nextTabs[Math.max(0, index - 1)];
            setActiveTab(nextTab.id);
            window.location.href = nextTab.url;
            return;
        }

        render();
    }

    newTabButton.addEventListener('click', () => {
        const tab = createTab(currentUrl(), currentTitle());
        const tabs = readTabs();
        tabs.push(tab);
        saveTabs(tabs);
        setActiveTab(tab.id);
        render();
    });

    render();

    let renderTimer = null;

    function scheduleTitleRefresh() {
        window.clearTimeout(renderTimer);
        renderTimer = window.setTimeout(() => {
            const tabs = readTabs();
            const activeTab = tabs.find((tab) => tab.id === getActiveTabId());

            if (!activeTab || activeTab.title !== currentTitle() || activeTab.url !== currentUrl()) {
                render();
            }
        }, 80);
    }

    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        const observer = new MutationObserver(scheduleTitleRefresh);
        observer.observe(mainContent, {
            attributes: true,
            childList: true,
            characterData: true,
            subtree: true,
        });
    }

    document.addEventListener('input', (event) => {
        if (event.target.matches('.tasks-issue-title-field input, #id_title, input[name="title"]')) {
            scheduleTitleRefresh();
        }
    });

    document.addEventListener('change', (event) => {
        if (event.target.matches('#board-selector, #workspace-selector')) {
            scheduleTitleRefresh();
        }
    });
})();
