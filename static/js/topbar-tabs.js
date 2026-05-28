(function () {
    const tabsEl = document.getElementById('topbar-tabs');
    const newTabButton = document.getElementById('topbar-new-tab');

    if (!tabsEl || !newTabButton) {
        return;
    }

    const tabsKey = 'ancoreTopbarTabs';
    const activeKey = 'ancoreActiveTopbarTab';
    const maxTabs = 12;
    const tabContentCache = new Map();

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

    function cacheActiveTabContent() {
        const activeId = getActiveTabId();
        const pageContainer = document.querySelector('.page-container');
        const secondaryPanel = document.querySelector('.secondary-menu-panel');

        if (!activeId || !pageContainer) {
            return;
        }

        const tabs = readTabs();
        const activeTab = tabs.find((tab) => tab.id === activeId);
        if (activeTab) {
            activeTab.url = currentUrl();
            activeTab.title = currentTitle();
            saveTabs(tabs);
        }

        tabContentCache.set(activeId, {
            url: currentUrl(),
            title: document.title,
            scrollX: window.scrollX,
            scrollY: window.scrollY,
            pageContainerClass: pageContainer.className,
            pageNodes: Array.from(pageContainer.childNodes),
            secondaryPanelClass: secondaryPanel ? secondaryPanel.className : '',
            secondaryPanelAttributes: secondaryPanel
                ? Array.from(secondaryPanel.attributes).map((attribute) => [attribute.name, attribute.value])
                : [],
            secondaryNodes: secondaryPanel ? Array.from(secondaryPanel.childNodes) : [],
        });
    }

    function restoreElementAttributes(element, attributes) {
        if (!element) {
            return;
        }

        Array.from(element.attributes).forEach((attribute) => {
            element.removeAttribute(attribute.name);
        });

        attributes.forEach(([name, value]) => {
            element.setAttribute(name, value);
        });
    }

    function attributesFrom(element) {
        return Array.from(element.attributes).map((attribute) => [attribute.name, attribute.value]);
    }

    function assetUrl(value, baseUrl = window.location.href) {
        return new URL(value, baseUrl).href;
    }

    function loadScript(script, baseUrl) {
        return new Promise((resolve, reject) => {
            const nextScript = document.createElement('script');

            Array.from(script.attributes).forEach((attribute) => {
                if (attribute.name !== 'defer') {
                    nextScript.setAttribute(attribute.name, attribute.value);
                }
            });

            if (script.src) {
                const src = assetUrl(script.getAttribute('src'), baseUrl);
                const srcUrl = new URL(src);
                const alreadyLoaded = Array.from(document.querySelectorAll('script[src]'))
                    .some((existingScript) => assetUrl(existingScript.getAttribute('src')) === src);

                if (alreadyLoaded && srcUrl.origin !== window.location.origin) {
                    resolve();
                    return;
                }

                nextScript.src = src;
                nextScript.async = false;
                nextScript.addEventListener('load', resolve, { once: true });
                nextScript.addEventListener('error', reject, { once: true });
                document.head.appendChild(nextScript);
                return;
            }

            nextScript.textContent = script.textContent;
            document.head.appendChild(nextScript);
            resolve();
        });
    }

    function syncHeadStyles(doc, baseUrl) {
        const existingStyles = new Set(
            Array.from(document.querySelectorAll('link[rel="stylesheet"][href]'))
                .map((link) => assetUrl(link.getAttribute('href')))
        );

        doc.querySelectorAll('head link[rel="stylesheet"][href]').forEach((link) => {
            const href = assetUrl(link.getAttribute('href'), baseUrl);
            if (existingStyles.has(href)) {
                return;
            }

            const nextLink = link.cloneNode(true);
            nextLink.href = href;
            document.head.appendChild(nextLink);
            existingStyles.add(href);
        });
    }

    async function runHeadScripts(doc, baseUrl) {
        for (const script of doc.querySelectorAll('head script')) {
            await loadScript(script, baseUrl);
        }
    }

    function syncSidebarActive(url) {
        const targetUrl = new URL(url, window.location.origin);
        const targetPath = targetUrl.pathname;

        document.querySelectorAll('.sidebar .nav-link.active').forEach((link) => {
            link.classList.remove('active');
        });

        const navLinks = Array.from(document.querySelectorAll('.sidebar .nav-section .nav-link[href]'));
        let bestMatch = null;

        navLinks.forEach((link) => {
            const href = link.getAttribute('href');
            if (!href || href.startsWith('#')) {
                return;
            }

            const linkPath = new URL(href, window.location.origin).pathname;
            if (
                targetPath === linkPath ||
                (linkPath !== '/' && targetPath.startsWith(linkPath.replace(/\/$/, '') + '/'))
            ) {
                if (!bestMatch || linkPath.length > new URL(bestMatch.getAttribute('href'), window.location.origin).pathname.length) {
                    bestMatch = link;
                }
            }
        });

        if (bestMatch) {
            bestMatch.classList.add('active');
        }
    }

    function restoreCachedTab(tab) {
        const cached = tabContentCache.get(tab.id);
        const pageContainer = document.querySelector('.page-container');
        const secondaryPanel = document.querySelector('.secondary-menu-panel');

        if (!cached || !pageContainer) {
            return false;
        }

        pageContainer.className = cached.pageContainerClass;
        pageContainer.replaceChildren(...cached.pageNodes);

        if (secondaryPanel) {
            restoreElementAttributes(secondaryPanel, cached.secondaryPanelAttributes);
            secondaryPanel.className = cached.secondaryPanelClass;
            secondaryPanel.replaceChildren(...cached.secondaryNodes);
        }

        document.title = cached.title || tab.title || document.title;
        if (currentUrl() !== tab.url) {
            window.history.pushState({ topbarTabId: tab.id }, '', tab.url);
        }

        syncSidebarActive(tab.url);
        window.scrollTo(cached.scrollX || 0, cached.scrollY || 0);
        return true;
    }

    async function loadTabFromServer(tab) {
        const targetUrl = new URL(tab.url, window.location.origin);
        if (targetUrl.origin !== window.location.origin) {
            return false;
        }

        const response = await fetch(targetUrl.href, {
            credentials: 'same-origin',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
        });

        if (!response.ok) {
            return false;
        }

        const html = await response.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const nextPageContainer = doc.querySelector('.page-container');
        const nextSecondaryPanel = doc.querySelector('.secondary-menu-panel');
        const pageContainer = document.querySelector('.page-container');
        const secondaryPanel = document.querySelector('.secondary-menu-panel');

        if (!nextPageContainer || !pageContainer) {
            return false;
        }

        syncHeadStyles(doc, targetUrl.href);

        restoreElementAttributes(pageContainer, attributesFrom(nextPageContainer));
        pageContainer.replaceChildren(...Array.from(nextPageContainer.childNodes));

        if (secondaryPanel && nextSecondaryPanel) {
            restoreElementAttributes(secondaryPanel, attributesFrom(nextSecondaryPanel));
            secondaryPanel.replaceChildren(...Array.from(nextSecondaryPanel.childNodes));
        } else if (secondaryPanel) {
            secondaryPanel.setAttribute('aria-hidden', 'true');
            secondaryPanel.replaceChildren();
        }

        document.title = doc.title || tab.title || document.title;
        window.history.pushState({ topbarTabId: tab.id }, '', targetUrl.href);
        syncSidebarActive(tab.url);
        window.scrollTo(0, 0);
        await runHeadScripts(doc, targetUrl.href);
        return true;
    }

    async function activateTab(tab) {
        if (tab.id === getActiveTabId()) {
            return;
        }

        cacheActiveTabContent();
        setActiveTab(tab.id);

        if (restoreCachedTab(tab)) {
            render();
            return;
        }

        if (tab.url !== currentUrl()) {
            try {
                if (await loadTabFromServer(tab)) {
                    render();
                    return;
                }
            } catch (error) {
                console.error('Nie udało się przełączyć karty bez odświeżania.', error);
            }

            window.location.href = tab.url;
        } else {
            render();
        }
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
                activateTab(tab);
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

    async function closeTab(tabId) {
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
            if (restoreCachedTab(nextTab)) {
                render();
                return;
            }

            try {
                if (await loadTabFromServer(nextTab)) {
                    render();
                    return;
                }
            } catch (error) {
                console.error('Nie udało się zamknąć karty bez odświeżania.', error);
            }

            window.location.href = nextTab.url;
            return;
        }

        tabContentCache.delete(tabId);
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
