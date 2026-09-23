(function () {
    const MQ_TABLET = window.matchMedia('(max-width: 1024px)');
    const MQ_MOBILE = window.matchMedia('(max-width: 767px)');
    const SECONDARY_MENU_MIN_WIDTH = 230;
    const SECONDARY_MENU_MAX_WIDTH = 500;
    const SECONDARY_MENU_CONTENT_MIN_WIDTH = 240;
    const SIDEBAR_MIN_WIDTH = 220;
    const SIDEBAR_MAX_WIDTH = 420;
    const SIDEBAR_DEFAULT_WIDTH = 272;
    const SIDEBAR_TRANSITION_MS = 360;
    const SIDEBAR_GROUPS_STORAGE_KEY = 'ancoreSidebarCollapsedGroups';
    const SIDEBAR_FAVORITES_STORAGE_KEY = 'ancoreSidebarFavoritesCollapsed';
    const SIDEBAR_COLLAPSED_STORAGE_KEY = 'ancoreSidebarCollapsed';
    const SIDEBAR_WIDTH_STORAGE_KEY = 'ancoreSidebarWidth';

    const sidebar = document.querySelector('.sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');
    const sidebarCollapseToggle = document.querySelector('[data-sidebar-collapse-toggle]');
    const sidebarResizer = document.querySelector('[data-sidebar-resizer]');
    const sidebarWorkspaceSwitcher = document.querySelector('[data-sidebar-workspace-switcher]');
    const sidebarWorkspaceToggle = document.querySelector('[data-sidebar-workspace-toggle]');
    const sidebarWorkspaceMenu = document.querySelector('[data-sidebar-workspace-menu]');
    const sidebarWorkspaceSearchInput = document.querySelector('[data-sidebar-workspace-search-input]');
    const sidebarWorkspaceSearchEmpty = document.querySelector('[data-sidebar-workspace-search-empty]');
    const sidebarSearchToggle = document.querySelector('[data-sidebar-search-toggle]');
    const sidebarSearch = document.querySelector('[data-sidebar-search]');
    const sidebarSearchInput = document.querySelector('[data-sidebar-search-input]');
    const sidebarSearchEmpty = document.querySelector('[data-sidebar-search-empty]');
    const sidebarFavoritesDropzone = document.querySelector('[data-sidebar-favorites-dropzone]');
    const sidebarFavoritesToggle = document.querySelector('[data-sidebar-favorites-toggle]');
    const sidebarFavoritesRemoveDropzone = document.querySelector('[data-sidebar-favorites-remove-dropzone]');
    const sidebarCollapsedFlyout = document.querySelector('[data-sidebar-collapsed-flyout]');
    const sidebarCollapsedFlyoutTitle = document.querySelector('[data-sidebar-collapsed-flyout-title]');
    const sidebarCollapsedFlyoutLinks = document.querySelector('[data-sidebar-collapsed-flyout-links]');
    const sidebarCollapsedFlyoutClose = document.querySelector('[data-sidebar-collapsed-flyout-close]');
    const secondaryMenu = document.getElementById('secondary-menu');
    const secondaryMenuToggle = document.getElementById('secondary-menu-toggle');
    const secondaryMenuResizer = document.getElementById('secondary-menu-resizer');
    const loadingOverlay = document.getElementById('app-loading-overlay');
    const root = document.documentElement;
    let sidebarResizeState = null;
    let secondaryMenuResizeState = null;
    let pageLoadingTimer = null;
    let pageLoadingFallbackTimer = null;
    let partialNavigationController = null;
    let sidebarCollapsedFlyoutTrigger = null;
    let sidebarTransitionTimer = null;

    function getUrl(href) {
        try {
            return new URL(href, window.location.href);
        } catch (error) {
            return null;
        }
    }

    function isPartialNavigationPath(pathname) {
        const appShellPaths = [
            /^\/$/,
            /^\/settings\/?$/,
            /^\/workplaces\/?$/,
            /^\/accounts\/profile\/?$/,
            /^\/tasks\/?$/,
            /^\/tasks\/groups\/\d+\/?$/,
            /^\/kanban\/?$/,
            /^\/kanban\/groups\/\d+\/?$/,
            /^\/contacts\/?$/,
            /^\/contacts\/users\/?$/,
            /^\/contacts\/companies\/?$/,
            /^\/contacts\/companies\/\d+\/?$/,
            /^\/contacts\/companies\/\d+\/edit\/?$/,
            /^\/contacts\/guests\/?$/,
            /^\/contacts\/shared\/?$/,
            /^\/contacts\/view-contact\/\d+\/?$/,
            /^\/contacts\/view-contact\/\d+\/edit\/?$/,
            /^\/calendar\/?$/,
        ];

        if (
            pathname.startsWith('/admin/')
            || pathname.startsWith('/static/')
            || pathname.startsWith('/media/')
            || pathname.startsWith('/accounts/login/')
            || pathname.startsWith('/accounts/logout/')
            || pathname.startsWith('/accounts/register/')
            || pathname.startsWith('/accounts/profile/add-account/')
            || pathname.startsWith('/accounts/profile/status/')
            || pathname.startsWith('/accounts/profile/switch-account/')
            || pathname.startsWith('/accounts/profile/remove-account/')
            || pathname.startsWith('/accounts/presence/')
            || pathname.startsWith('/calendar/events/')
            || pathname.includes('/lookup/')
            || pathname.includes('/delete')
            || pathname.includes('/update/')
            || pathname.includes('/bulk-update-status/')
            || pathname.includes('/reorder-columns/')
            || pathname.includes('/share/')
        ) {
            return false;
        }

        return appShellPaths.some(pattern => pattern.test(pathname));
    }

    function canUsePartialNavigation(href) {
        // Editors need a full navigation so beforeunload protects unsaved work.
        if (document.querySelector('[data-app-full-navigation]')) return false;
        const url = getUrl(href);
        if (!url || url.origin !== window.location.origin) {
            return false;
        }

        return isPartialNavigationPath(url.pathname);
    }

    function syncSidebarState(nextDocument) {
        const currentLinks = document.querySelectorAll('.sidebar .nav-link');
        const nextLinks = nextDocument.querySelectorAll('.sidebar .nav-link');

        currentLinks.forEach(function (link, index) {
            const nextLink = nextLinks[index];
            if (!nextLink) return;

            link.className = nextLink.className;
            if (nextLink.hasAttribute('aria-current')) {
                link.setAttribute('aria-current', nextLink.getAttribute('aria-current'));
            } else {
                link.removeAttribute('aria-current');
            }
        });

        const currentViewItems = document.querySelectorAll('.sidebar-view-switcher__item');
        const nextViewItems = nextDocument.querySelectorAll('.sidebar-view-switcher__item');

        currentViewItems.forEach(function (item, index) {
            const nextItem = nextViewItems[index];
            if (!nextItem) return;

            item.className = nextItem.className;
            if (nextItem.hasAttribute('aria-current')) {
                item.setAttribute('aria-current', nextItem.getAttribute('aria-current'));
            } else {
                item.removeAttribute('aria-current');
            }
        });

        syncFavoriteActiveStates();
    }

    function assetUrl(url) {
        try {
            return new URL(url, window.location.href).href;
        } catch (error) {
            return '';
        }
    }

    function copyAttributes(from, to) {
        Array.from(from.attributes).forEach(attribute => {
            to.setAttribute(attribute.name, attribute.value);
        });
    }

    function hasLoadedAsset(selector, property, value) {
        return Array.from(document.querySelectorAll(selector)).some(element => element[property] === value);
    }

    function loadMissingStyles(nextDocument) {
        nextDocument.querySelectorAll('link[rel~="stylesheet"][href]').forEach(link => {
            const href = assetUrl(link.getAttribute('href'));
            if (!href || hasLoadedAsset('link[rel~="stylesheet"][href]', 'href', href)) {
                return;
            }

            const clone = link.cloneNode(false);
            clone.href = href;
            document.head.appendChild(clone);
        });
    }

    function loadMissingExternalScripts(nextDocument) {
        const loadingScripts = [];

        nextDocument.querySelectorAll('script[src]').forEach(script => {
            const src = assetUrl(script.getAttribute('src'));
            if (!src || hasLoadedAsset('script[src]', 'src', src)) {
                return;
            }

            const clone = document.createElement('script');
            copyAttributes(script, clone);
            clone.src = src;
            clone.async = false;
            loadingScripts.push(new Promise(resolve => {
                clone.addEventListener('load', resolve, { once: true });
                clone.addEventListener('error', resolve, { once: true });
            }));
            document.body.appendChild(clone);
        });

        return Promise.all(loadingScripts);
    }

    function runInlineScripts(scope) {
        if (!scope) return;

        scope.querySelectorAll('script').forEach(script => {
            const replacement = document.createElement('script');
            copyAttributes(script, replacement);
            if (script.src) {
                replacement.src = script.src;
            } else {
                replacement.textContent = script.textContent;
            }
            script.replaceWith(replacement);
        });
    }

    function updateTasksUiBodyClass() {
        document.body.classList.toggle('tasks-ui', Boolean(document.querySelector('.tasks-page')));
    }

    function clearTransientPageState() {
        document.body.classList.remove(
            'modal-open',
            'profile-edit-modal-open',
            'contacts-photo-editor-open',
            'is-resizing-directory-columns'
        );
    }

    function scrollAfterNavigation(url) {
        if (url.hash) {
            const targetId = decodeURIComponent(url.hash.slice(1));
            const target = targetId ? document.getElementById(targetId) : null;
            if (target) {
                target.scrollIntoView({ block: 'start' });
                return;
            }
        }

        window.scrollTo({ top: 0, left: 0 });
        document.querySelector('.main-content')?.scrollTo({ top: 0, left: 0 });
    }

    function replaceAppRegion(selector, nextDocument) {
        const currentElement = document.querySelector(selector);
        const nextElement = nextDocument.querySelector(selector);

        if (!currentElement || !nextElement) {
            return false;
        }

        currentElement.replaceWith(nextElement.cloneNode(true));
        return true;
    }

    async function finishPartialNavigation(nextDocument, url, options) {
        const hasRequiredRegions = document.querySelector('.main-content .page-container')
            && document.querySelector('#app-page-modals')
            && document.querySelector('#app-notifications')
            && nextDocument.querySelector('.main-content .page-container')
            && nextDocument.querySelector('#app-page-modals')
            && nextDocument.querySelector('#app-notifications');

        // A different account may have logged in in another tab. Reload the
        // whole shell so personal widgets cannot survive an identity change.
        const sameAccount = document.body.dataset.accountId === nextDocument.body.dataset.accountId;
        if (!hasRequiredRegions || !sameAccount) {
            window.location.href = url.href;
            return;
        }

        loadMissingStyles(nextDocument);

        const nextTitle = nextDocument.querySelector('title');
        if (nextTitle) {
            document.title = nextTitle.textContent;
        }

        clearTransientPageState();
        syncSidebarState(nextDocument);

        const pageUpdated = replaceAppRegion('.main-content .page-container', nextDocument);
        const modalsUpdated = replaceAppRegion('#app-page-modals', nextDocument);
        const notificationsUpdated = replaceAppRegion('#app-notifications', nextDocument);

        if (!pageUpdated || !modalsUpdated || !notificationsUpdated) {
            window.location.href = url.href;
            return;
        }

        runInlineScripts(document.querySelector('.main-content .page-container'));
        runInlineScripts(document.querySelector('#app-page-modals'));
        await loadMissingExternalScripts(nextDocument);

        if (options?.updateHistory !== false) {
            const historyMethod = options?.replace ? 'replaceState' : 'pushState';
            window.history[historyMethod]({ ancorePartialNavigation: true }, '', url.href);
        }

        updateTasksUiBodyClass();
        scrollAfterNavigation(url);
        [
            document.querySelector('.main-content .page-container'),
            document.querySelector('#app-page-modals'),
            document.querySelector('#app-notifications')
        ].forEach(region => window.AncoreIcons?.render(region));
        document.dispatchEvent(new CustomEvent('ancore:content-loaded', { detail: { url: url.href } }));
    }

    async function navigatePartially(href, options) {
        const url = getUrl(href);
        if (!url || !canUsePartialNavigation(url.href)) {
            return false;
        }

        if (partialNavigationController) {
            partialNavigationController.abort();
        }

        const navigationController = typeof AbortController === 'function' ? new AbortController() : null;
        partialNavigationController = navigationController;
        document.body.classList.add('app-partial-navigation');
        requestPageLoading();

        try {
            const requestOptions = {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'text/html',
                },
                credentials: 'same-origin',
            };

            if (navigationController) {
                requestOptions.signal = navigationController.signal;
            }

            const response = await fetch(url.href, requestOptions);

            if (!response.ok) {
                window.location.href = url.href;
                return true;
            }

            const html = await response.text();
            const nextDocument = new DOMParser().parseFromString(html, 'text/html');
            const responseUrl = getUrl(response.url) || url;

            await finishPartialNavigation(nextDocument, responseUrl, options);
        } catch (error) {
            if (error.name !== 'AbortError') {
                window.location.href = url.href;
            }
        } finally {
            if (!navigationController || partialNavigationController === navigationController) {
                partialNavigationController = null;
                document.body.classList.remove('app-partial-navigation');
                hidePageLoading();
            }
        }

        return true;
    }

    window.AncoreApp = Object.assign(window.AncoreApp || {}, {
        canNavigatePartially: canUsePartialNavigation,
        navigate: navigatePartially,
    });

    function setPageLoading(loading) {
        root.classList.toggle('app-page-loading', loading);
        document.body.classList.toggle('app-page-loading', loading);

        if (loadingOverlay) {
            loadingOverlay.setAttribute('aria-hidden', loading ? 'false' : 'true');
        }
    }

    function showPageLoading(options) {
        window.clearTimeout(pageLoadingTimer);
        window.clearTimeout(pageLoadingFallbackTimer);
        setPageLoading(true);

        if (options?.autoHide) {
            pageLoadingFallbackTimer = window.setTimeout(hidePageLoading, 12000);
        }
    }

    function requestPageLoading() {
        window.clearTimeout(pageLoadingTimer);
        pageLoadingTimer = window.setTimeout(function () {
            showPageLoading({ autoHide: true });
        }, 90);
    }

    function hidePageLoading() {
        window.clearTimeout(pageLoadingTimer);
        window.clearTimeout(pageLoadingFallbackTimer);
        setPageLoading(false);
    }

    function shouldIgnoreNavigationClick(e) {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
            return true;
        }

        const target = e.target instanceof Element ? e.target : e.target?.parentElement;
        const link = target?.closest('a[href]');
        if (!link || link.hasAttribute('download')) {
            return true;
        }

        const targetWindow = link.getAttribute('target');
        if (targetWindow && targetWindow !== '_self') {
            return true;
        }

        const href = (link.getAttribute('href') || '').trim();
        if (!href || href.startsWith('#') || /^(javascript|mailto|tel):/i.test(href)) {
            return true;
        }

        try {
            const url = new URL(link.href, window.location.href);
            const isSameDocument = url.origin === window.location.origin
                && url.pathname === window.location.pathname
                && url.search === window.location.search;

            return url.origin !== window.location.origin || (isSameDocument && Boolean(url.hash));
        } catch (error) {
            return true;
        }
    }

    function shouldIgnoreFormSubmit(e) {
        if (e.defaultPrevented) {
            return true;
        }

        const form = e.target;
        if (!(form instanceof HTMLFormElement)) {
            return true;
        }

        const submitter = e.submitter;
        const targetWindow = submitter?.getAttribute('formtarget') || form.getAttribute('target');
        const method = (submitter?.getAttribute('formmethod') || form.getAttribute('method') || '').toLowerCase();

        return method === 'dialog' || (targetWindow && targetWindow !== '_self');
    }

    if (root.classList.contains('app-page-loading')) {
        setPageLoading(true);
    }

    document.addEventListener('click', function (e) {
        if (shouldIgnoreNavigationClick(e)) {
            return;
        }

        const target = e.target instanceof Element ? e.target : e.target?.parentElement;
        const link = target?.closest('a[href]');
        if (link && canUsePartialNavigation(link.href)) {
            e.preventDefault();
            navigatePartially(link.href);
            return;
        }

        window.setTimeout(function () {
            if (!e.defaultPrevented) {
                requestPageLoading();
            }
        }, 0);
    });

    if (canUsePartialNavigation(window.location.href)) {
        window.history.replaceState({ ancorePartialNavigation: true }, '', window.location.href);
    }

    window.addEventListener('popstate', function () {
        if (!canUsePartialNavigation(window.location.href)) {
            return;
        }

        navigatePartially(window.location.href, { replace: true, updateHistory: false });
    });

    document.addEventListener('submit', function (e) {
        if (shouldIgnoreFormSubmit(e)) {
            return;
        }

        window.setTimeout(function () {
            if (!e.defaultPrevented) {
                requestPageLoading();
            }
        }, 0);
    });

    window.addEventListener('beforeunload', function (event) {
        showPageLoading();
        // A later listener can cancel leaving an editor. Clear the scrim if it does.
        window.setTimeout(function () {
            if (event.defaultPrevented) hidePageLoading();
        }, 0);
    });
    window.addEventListener('pagehide', function (e) {
        if (!e.persisted) {
            showPageLoading();
        }
    });
    window.addEventListener('pageshow', hidePageLoading);
    window.addEventListener('load', function () {
        window.setTimeout(hidePageLoading, 180);
    });
    window.addEventListener('focus', function () {
        if (document.visibilityState === 'visible') {
            window.setTimeout(hidePageLoading, 120);
        }
    });

    if (!sidebar) {
        root.classList.remove('app-shell-booting');
        return;
    }

    function isOverlayMode() {
        return MQ_MOBILE.matches;
    }

    function isSidebarCollapsedMode() {
        return !isOverlayMode() && root.classList.contains('sidebar-collapsed');
    }

    function updateSidebarGroupToggleA11y(group) {
        const toggleButton = group?.querySelector('[data-sidebar-group-toggle]');
        if (!toggleButton) return;

        const groupName = toggleButton.dataset.sidebarGroupName || '';
        const subnavId = toggleButton.dataset.sidebarSubnavId || toggleButton.getAttribute('aria-controls');
        if (subnavId) {
            toggleButton.dataset.sidebarSubnavId = subnavId;
        }

        if (isSidebarCollapsedMode() && sidebarCollapsedFlyout) {
            const open = sidebarCollapsedFlyoutTrigger === toggleButton && !sidebarCollapsedFlyout.hidden;
            const action = open ? 'Zamknij' : 'Otwórz';
            const accessibleLabel = `${action} menu ${groupName}`.trim();
            toggleButton.setAttribute('aria-controls', sidebarCollapsedFlyout.id);
            toggleButton.setAttribute('aria-expanded', open ? 'true' : 'false');
            toggleButton.setAttribute('aria-label', accessibleLabel);
            toggleButton.setAttribute('title', accessibleLabel);
            return;
        }

        const collapsed = group.classList.contains('is-collapsed');
        const action = collapsed ? 'Rozwiń' : 'Zwiń';
        const accessibleLabel = `${action} sekcję ${groupName}`.trim();
        if (subnavId) {
            toggleButton.setAttribute('aria-controls', subnavId);
        }
        toggleButton.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        toggleButton.setAttribute('aria-label', accessibleLabel);
        toggleButton.setAttribute('title', accessibleLabel);
    }

    function syncSidebarGroupToggleA11y() {
        sidebar.querySelectorAll('[data-sidebar-group]').forEach(updateSidebarGroupToggleA11y);
    }

    function closeCollapsedSidebarFlyout(options) {
        if (!sidebarCollapsedFlyout) return;

        const trigger = sidebarCollapsedFlyoutTrigger;
        sidebarCollapsedFlyout.hidden = true;
        sidebarCollapsedFlyoutLinks?.replaceChildren();
        trigger?.closest('[data-sidebar-group]')?.classList.remove('is-flyout-open');
        sidebarCollapsedFlyoutTrigger = null;
        if (trigger) {
            updateSidebarGroupToggleA11y(trigger.closest('[data-sidebar-group]'));
            if (options?.restoreFocus) trigger.focus();
        }
    }

    function positionCollapsedSidebarFlyout(toggleButton) {
        if (!sidebarCollapsedFlyout || sidebarCollapsedFlyout.hidden) return;

        const triggerRect = toggleButton.getBoundingClientRect();
        const sidebarRect = sidebar.getBoundingClientRect();
        const viewportPadding = 12;
        const top = Math.min(
            Math.max(viewportPadding, triggerRect.top),
            Math.max(viewportPadding, window.innerHeight - sidebarCollapsedFlyout.offsetHeight - viewportPadding)
        );
        const left = Math.min(
            Math.max(triggerRect.right, sidebarRect.right) + 8,
            Math.max(viewportPadding, window.innerWidth - sidebarCollapsedFlyout.offsetWidth - viewportPadding)
        );

        sidebarCollapsedFlyout.style.top = `${Math.round(top)}px`;
        sidebarCollapsedFlyout.style.left = `${Math.round(left)}px`;
    }

    function openCollapsedSidebarFlyout(group, focusFirstLink) {
        if (!sidebarCollapsedFlyout || !sidebarCollapsedFlyoutTitle || !sidebarCollapsedFlyoutLinks) return;

        const toggleButton = group.querySelector('[data-sidebar-group-toggle]');
        const subnavId = toggleButton?.dataset.sidebarSubnavId || toggleButton?.getAttribute('aria-controls');
        const sourceSubnav = subnavId ? document.getElementById(subnavId) : null;
        if (!toggleButton || !sourceSubnav) return;

        closeCollapsedSidebarFlyout();
        setWorkspaceMenuOpen(false);

        sidebarCollapsedFlyoutTitle.textContent = toggleButton.dataset.sidebarGroupName || '';
        sourceSubnav.querySelectorAll('a.sidebar-subnav-link').forEach(function (sourceLink) {
            const flyoutLink = sourceLink.cloneNode(true);
            flyoutLink.classList.remove('nav-link', 'sidebar-subnav-link');
            flyoutLink.classList.add('sidebar-collapsed-flyout__link');
            flyoutLink.removeAttribute('draggable');
            flyoutLink.removeAttribute('hidden');
            flyoutLink.setAttribute('title', sourceLink.textContent.trim());
            sidebarCollapsedFlyoutLinks.appendChild(flyoutLink);
        });

        sidebarCollapsedFlyoutTrigger = toggleButton;
        group.classList.add('is-flyout-open');
        sidebarCollapsedFlyout.hidden = false;
        updateSidebarGroupToggleA11y(group);
        positionCollapsedSidebarFlyout(toggleButton);
        window.AncoreIcons?.render(sidebarCollapsedFlyout);

        if (focusFirstLink) {
            sidebarCollapsedFlyoutLinks.querySelector('a')?.focus({ preventScroll: true });
        }
    }

    function updateSidebarCollapseA11y() {
        if (!sidebarCollapseToggle) return;

        if (isOverlayMode()) {
            const open = document.body.classList.contains('sidebar-open');
            sidebarCollapseToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
            sidebarCollapseToggle.setAttribute('aria-label', 'Zamknij menu boczne');
            sidebarCollapseToggle.setAttribute('title', 'Zamknij menu boczne');
            return;
        }

        const collapsed = root.classList.contains('sidebar-collapsed');
        const label = collapsed ? 'Rozwiń menu boczne' : 'Zwiń menu boczne';
        sidebarCollapseToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        sidebarCollapseToggle.setAttribute('aria-label', label);
        sidebarCollapseToggle.setAttribute('title', label);
    }

    function setOpen(open) {
        const on = open && isOverlayMode();
        document.body.classList.toggle('sidebar-open', on);
        sidebar.classList.toggle('sidebar--visible', on);
        if (toggle) {
            toggle.setAttribute('aria-expanded', on ? 'true' : 'false');
            toggle.setAttribute('aria-label', on ? 'Zamknij menu' : 'Otwórz menu');
        }
        updateSidebarCollapseA11y();
    }

    function closeSidebar() {
        setOpen(false);
    }

    function readSidebarCollapsed() {
        try {
            return window.localStorage.getItem(SIDEBAR_COLLAPSED_STORAGE_KEY) === 'true';
        } catch (error) {
            return false;
        }
    }

    function readSidebarWidth() {
        try {
            const width = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
            return Number.isFinite(width) && width > 0 ? width : null;
        } catch (error) {
            return null;
        }
    }

    function getSidebarResizeBounds() {
        return {
            min: SIDEBAR_MIN_WIDTH,
            max: Math.min(
                SIDEBAR_MAX_WIDTH,
                Math.max(SIDEBAR_MIN_WIDTH, window.innerWidth - 360)
            ),
        };
    }

    function clampSidebarWidth(width) {
        const bounds = getSidebarResizeBounds();
        return Math.min(bounds.max, Math.max(bounds.min, width));
    }

    function currentSidebarWidth() {
        return sidebar.offsetWidth || sidebar.getBoundingClientRect().width;
    }

    function updateSidebarResizeA11y(width) {
        if (!sidebarResizer) return;

        const bounds = getSidebarResizeBounds();
        const roundedWidth = Math.round(width);
        sidebarResizer.setAttribute('aria-valuemin', String(bounds.min));
        sidebarResizer.setAttribute('aria-valuemax', String(bounds.max));
        sidebarResizer.setAttribute('aria-valuenow', String(roundedWidth));
        sidebarResizer.setAttribute('aria-valuetext', `${roundedWidth} pikseli`);
    }

    function setSidebarWidth(width, persist) {
        const nextWidth = clampSidebarWidth(width);
        root.style.setProperty('--sidebar-width', `${nextWidth}px`);
        updateSidebarResizeA11y(nextWidth);

        if (persist) {
            try {
                window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(Math.round(nextWidth)));
            } catch (error) {
                // Resizing still works for this page when localStorage is unavailable.
            }
        }
    }

    function syncSidebarWidthForViewport() {
        if (isOverlayMode()) {
            root.style.removeProperty('--sidebar-width');
            return;
        }

        const savedWidth = readSidebarWidth();
        if (savedWidth !== null) {
            setSidebarWidth(savedWidth, false);
        } else {
            updateSidebarResizeA11y(currentSidebarWidth());
        }
    }

    function setWorkspaceMenuOpen(open) {
        if (!sidebarWorkspaceToggle || !sidebarWorkspaceMenu) return;

        sidebarWorkspaceToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        sidebarWorkspaceMenu.hidden = !open;

        if (open) {
            window.setTimeout(function () {
                sidebarWorkspaceSearchInput?.focus({ preventScroll: true });
            }, 0);
        } else if (sidebarWorkspaceSearchInput) {
            sidebarWorkspaceSearchInput.value = '';
            applyWorkspaceSearch();
        }
    }

    function normalizeSidebarSearch(value) {
        return (value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLocaleLowerCase('pl')
            .replace(/ł/g, 'l')
            .trim();
    }

    function applyWorkspaceSearch() {
        if (!sidebarWorkspaceSearchInput || !sidebarWorkspaceMenu) return;

        const query = normalizeSidebarSearch(sidebarWorkspaceSearchInput.value);
        let visibleItems = 0;

        sidebarWorkspaceMenu.querySelectorAll('[data-sidebar-workspace-item]').forEach(function (item) {
            const searchText = item.dataset.sidebarWorkspaceSearchText || item.textContent;
            const matches = !query || normalizeSidebarSearch(searchText).includes(query);
            item.hidden = !matches;
            if (matches) visibleItems += 1;
        });

        if (sidebarWorkspaceSearchEmpty) {
            sidebarWorkspaceSearchEmpty.hidden = !query || visibleItems > 0;
        }
    }

    function applySidebarSearch() {
        if (!sidebarSearchInput) return;

        const query = normalizeSidebarSearch(sidebarSearchInput.value);
        let visibleItems = 0;

        sidebar.querySelector('.sidebar-menu-section--favorites')?.toggleAttribute('hidden', Boolean(query));

        sidebar.querySelectorAll('[data-sidebar-group]').forEach(function (group) {
            const primaryButton = group.querySelector('[data-sidebar-group-toggle]');
            const subnav = primaryButton?.getAttribute('aria-controls')
                ? document.getElementById(primaryButton.getAttribute('aria-controls'))
                : null;
            const subnavLinks = Array.from(group.querySelectorAll('.sidebar-subnav-link'));
            const primaryMatches = !query || normalizeSidebarSearch(primaryButton?.textContent).includes(query);
            let matchingSubnavItems = 0;

            subnavLinks.forEach(function (link) {
                const matches = !query || primaryMatches || normalizeSidebarSearch(link.textContent).includes(query);
                link.hidden = !matches;
                link.closest('[data-sidebar-source-item]')?.toggleAttribute('hidden', !matches);
                if (matches) matchingSubnavItems += 1;
            });

            const groupMatches = primaryMatches || matchingSubnavItems > 0;
            group.hidden = !groupMatches;
            if (groupMatches) visibleItems += 1;

            if (subnav) {
                if (query && matchingSubnavItems > 0) {
                    subnav.hidden = false;
                    group.classList.add('is-search-expanded');
                } else {
                    group.classList.remove('is-search-expanded');
                    subnav.hidden = group.classList.contains('is-collapsed');
                }
            }
        });

        sidebar.querySelectorAll('.sidebar-primary-link--standalone').forEach(function (link) {
            const matches = !query || normalizeSidebarSearch(link.textContent).includes(query);
            link.hidden = !matches;
            link.closest('[data-sidebar-source-item]')?.toggleAttribute('hidden', !matches);
            if (matches) visibleItems += 1;
        });

        if (sidebarSearchEmpty) {
            sidebarSearchEmpty.hidden = !query || visibleItems > 0;
        }
    }

    function setSidebarSearchOpen(open) {
        if (!sidebarSearchToggle || !sidebarSearch) return;

        sidebarSearchToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        sidebarSearch.hidden = !open;
        sidebar.classList.toggle('is-searching', open);

        if (open) {
            setWorkspaceMenuOpen(false);
            window.setTimeout(function () {
                sidebarSearchInput?.focus({ preventScroll: true });
            }, 0);
        } else if (sidebarSearchInput) {
            sidebarSearchInput.value = '';
            applySidebarSearch();
        }
    }

    function finishSidebarTransition() {
        if (sidebarTransitionTimer !== null) {
            window.clearTimeout(sidebarTransitionTimer);
            sidebarTransitionTimer = null;
        }

        root.classList.remove(
            'sidebar-transitioning',
            'sidebar-is-collapsing',
            'sidebar-is-expanding'
        );
    }

    function beginSidebarTransition(collapsed) {
        finishSidebarTransition();

        if (
            isOverlayMode()
            || window.matchMedia('(prefers-reduced-motion: reduce)').matches
        ) {
            return;
        }

        root.classList.add(
            'sidebar-transitioning',
            collapsed ? 'sidebar-is-collapsing' : 'sidebar-is-expanding'
        );
        sidebarTransitionTimer = window.setTimeout(
            finishSidebarTransition,
            SIDEBAR_TRANSITION_MS + 80
        );
    }

    function setSidebarCollapsed(collapsed, persist) {
        const stateChanged = root.classList.contains('sidebar-collapsed') !== collapsed;

        if (persist && stateChanged) {
            beginSidebarTransition(collapsed);
        } else if (!persist) {
            finishSidebarTransition();
        }

        closeCollapsedSidebarFlyout();
        root.classList.toggle('sidebar-collapsed', collapsed);
        document.body.classList.toggle('sidebar-collapsed', collapsed);
        updateSidebarCollapseA11y();
        syncSidebarGroupToggleA11y();
        syncSidebarFavoritesVisibility();

        if (collapsed) {
            setWorkspaceMenuOpen(false);
            setSidebarSearchOpen(false);
        }

        if (persist) {
            try {
                window.localStorage.setItem(SIDEBAR_COLLAPSED_STORAGE_KEY, collapsed ? 'true' : 'false');
            } catch (error) {
                // Collapsing still works for this page when localStorage is unavailable.
            }
        }

        if (!collapsed && !isOverlayMode()) {
            window.setTimeout(function () {
                if (!root.classList.contains('sidebar-collapsed')) {
                    updateSidebarResizeA11y(currentSidebarWidth());
                }
            }, 180);
        }
    }

    sidebar?.addEventListener('transitionend', function (event) {
        if (
            event.target === sidebar
            && event.propertyName === 'width'
            && root.classList.contains('sidebar-transitioning')
        ) {
            finishSidebarTransition();
        }
    });

    setSidebarCollapsed(readSidebarCollapsed(), false);
    syncSidebarWidthForViewport();

    if (sidebarResizer) {
        sidebarResizer.addEventListener('pointerdown', function (event) {
            if (
                !event.isPrimary
                || event.button !== 0
                || isOverlayMode()
                || root.classList.contains('sidebar-collapsed')
            ) {
                return;
            }

            event.preventDefault();
            sidebarResizer.setPointerCapture?.(event.pointerId);
            sidebarResizeState = {
                pointerId: event.pointerId,
                startX: event.clientX,
                startWidth: currentSidebarWidth(),
            };
            document.body.classList.add('sidebar-resizing');
        });

        window.addEventListener('pointermove', function (event) {
            if (!sidebarResizeState || event.pointerId !== sidebarResizeState.pointerId) return;

            event.preventDefault();
            setSidebarWidth(
                sidebarResizeState.startWidth + event.clientX - sidebarResizeState.startX,
                false
            );
        });

        function finishSidebarResize(event) {
            if (!sidebarResizeState || event.pointerId !== sidebarResizeState.pointerId) return;

            if (sidebarResizer.hasPointerCapture?.(event.pointerId)) {
                sidebarResizer.releasePointerCapture(event.pointerId);
            }
            sidebarResizeState = null;
            document.body.classList.remove('sidebar-resizing');
            setSidebarWidth(currentSidebarWidth(), true);
        }

        window.addEventListener('pointerup', finishSidebarResize);
        window.addEventListener('pointercancel', finishSidebarResize);

        sidebarResizer.addEventListener('keydown', function (event) {
            if (isOverlayMode() || root.classList.contains('sidebar-collapsed')) return;

            const bounds = getSidebarResizeBounds();
            const step = event.shiftKey ? 24 : 8;
            let nextWidth = null;

            if (event.key === 'ArrowLeft') nextWidth = currentSidebarWidth() - step;
            if (event.key === 'ArrowRight') nextWidth = currentSidebarWidth() + step;
            if (event.key === 'Home') nextWidth = bounds.min;
            if (event.key === 'End') nextWidth = bounds.max;
            if (nextWidth === null) return;

            event.preventDefault();
            setSidebarWidth(nextWidth, true);
        });

        sidebarResizer.addEventListener('dblclick', function () {
            if (isOverlayMode() || root.classList.contains('sidebar-collapsed')) return;
            setSidebarWidth(SIDEBAR_DEFAULT_WIDTH, true);
        });
    }

    sidebarWorkspaceToggle?.addEventListener('click', function (event) {
        event.stopPropagation();
        closeCollapsedSidebarFlyout();
        const open = sidebarWorkspaceToggle.getAttribute('aria-expanded') !== 'true';
        setSidebarSearchOpen(false);
        setWorkspaceMenuOpen(open);
    });

    sidebarWorkspaceMenu?.addEventListener('keydown', function (event) {
        const items = Array.from(sidebarWorkspaceMenu.querySelectorAll('[role="menuitem"]')).filter(function (item) {
            const workspaceItem = item.closest('[data-sidebar-workspace-item]');
            return !workspaceItem || !workspaceItem.hidden;
        });
        const currentIndex = items.indexOf(document.activeElement);

        if (event.key === 'Escape') {
            event.preventDefault();
            setWorkspaceMenuOpen(false);
            sidebarWorkspaceToggle?.focus();
        } else if (event.key === 'ArrowDown' && items.length) {
            event.preventDefault();
            items[(currentIndex + 1) % items.length].focus();
        } else if (event.key === 'ArrowUp' && items.length) {
            event.preventDefault();
            items[(currentIndex - 1 + items.length) % items.length].focus();
        }
    });

    sidebarWorkspaceSearchInput?.addEventListener('input', applyWorkspaceSearch);

    sidebarSearchToggle?.addEventListener('click', function () {
        setSidebarSearchOpen(sidebarSearchToggle.getAttribute('aria-expanded') !== 'true');
    });

    sidebarSearchInput?.addEventListener('input', applySidebarSearch);
    sidebarSearchInput?.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            event.preventDefault();
            setSidebarSearchOpen(false);
            sidebarSearchToggle?.focus();
        }
    });

    sidebarCollapseToggle?.addEventListener('click', function () {
        if (isOverlayMode()) {
            closeSidebar();
            return;
        }

        setSidebarCollapsed(!root.classList.contains('sidebar-collapsed'), true);
    });

    document.addEventListener('click', function (event) {
        if (sidebarWorkspaceSwitcher && !sidebarWorkspaceSwitcher.contains(event.target)) {
            setWorkspaceMenuOpen(false);
        }
        if (
            sidebarCollapsedFlyout
            && !sidebarCollapsedFlyout.hidden
            && !sidebarCollapsedFlyout.contains(event.target)
            && !sidebarCollapsedFlyoutTrigger?.contains(event.target)
        ) {
            closeCollapsedSidebarFlyout();
        }
    });

    function readCollapsedSidebarGroups() {
        try {
            const value = JSON.parse(window.localStorage.getItem(SIDEBAR_GROUPS_STORAGE_KEY) || '[]');
            return new Set(Array.isArray(value) ? value : []);
        } catch (error) {
            return new Set();
        }
    }

    function saveCollapsedSidebarGroups(collapsedGroups) {
        try {
            window.localStorage.setItem(SIDEBAR_GROUPS_STORAGE_KEY, JSON.stringify([...collapsedGroups]));
        } catch (error) {
            // Collapsing still works for this page when localStorage is unavailable.
        }
    }

    function readSidebarFavoritesCollapsed() {
        try {
            return window.localStorage.getItem(SIDEBAR_FAVORITES_STORAGE_KEY) === 'true';
        } catch (error) {
            return false;
        }
    }

    function syncSidebarFavoritesVisibility() {
        const content = sidebarFavoritesDropzone?.querySelector('[data-sidebar-favorites-content]');
        if (!content) return;

        const collapsed = sidebarFavoritesDropzone.classList.contains('is-collapsed');
        content.hidden = collapsed;
    }

    function setSidebarFavoritesCollapsed(collapsed, persist) {
        if (!sidebarFavoritesDropzone || !sidebarFavoritesToggle) return;

        const action = collapsed ? 'Rozwiń' : 'Zwiń';
        sidebarFavoritesDropzone.classList.toggle('is-collapsed', collapsed);
        sidebarFavoritesToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        sidebarFavoritesToggle.setAttribute('aria-label', `${action} sekcję Favorites`);
        sidebarFavoritesToggle.setAttribute('title', `${action} sekcję Favorites`);
        syncSidebarFavoritesVisibility();

        if (persist) {
            try {
                window.localStorage.setItem(SIDEBAR_FAVORITES_STORAGE_KEY, collapsed ? 'true' : 'false');
            } catch (error) {
                // Collapsing still works for this page when localStorage is unavailable.
            }
        }
    }

    setSidebarFavoritesCollapsed(readSidebarFavoritesCollapsed(), false);
    sidebarFavoritesToggle?.addEventListener('click', function () {
        setSidebarFavoritesCollapsed(sidebarFavoritesToggle.getAttribute('aria-expanded') === 'true', true);
    });

    function setSidebarGroupCollapsed(group, collapsed) {
        const toggleButton = group.querySelector('[data-sidebar-group-toggle]');
        const subnavId = toggleButton?.dataset.sidebarSubnavId || toggleButton?.getAttribute('aria-controls');
        const subnav = subnavId ? document.getElementById(subnavId) : null;

        if (toggleButton && subnavId) {
            toggleButton.dataset.sidebarSubnavId = subnavId;
        }

        group.classList.toggle('is-collapsed', collapsed);
        subnav?.toggleAttribute('hidden', collapsed);
        updateSidebarGroupToggleA11y(group);
    }

    const collapsedSidebarGroups = readCollapsedSidebarGroups();
    sidebar.querySelectorAll('[data-sidebar-group]').forEach(function (group) {
        const groupKey = group.dataset.sidebarGroup;
        const toggleButton = group.querySelector('[data-sidebar-group-toggle]');

        if (!groupKey || !toggleButton) {
            return;
        }

        setSidebarGroupCollapsed(group, collapsedSidebarGroups.has(groupKey));
        toggleButton.addEventListener('click', function (event) {
            if (isSidebarCollapsedMode()) {
                const isCurrentFlyout = sidebarCollapsedFlyoutTrigger === toggleButton
                    && sidebarCollapsedFlyout
                    && !sidebarCollapsedFlyout.hidden;
                if (isCurrentFlyout) {
                    closeCollapsedSidebarFlyout({ restoreFocus: true });
                } else {
                    openCollapsedSidebarFlyout(group, event.detail === 0);
                }
                return;
            }

            const collapsed = toggleButton.getAttribute('aria-expanded') === 'true';
            setSidebarGroupCollapsed(group, collapsed);

            if (collapsed) {
                collapsedSidebarGroups.add(groupKey);
            } else {
                collapsedSidebarGroups.delete(groupKey);
            }

            saveCollapsedSidebarGroups(collapsedSidebarGroups);
        });
    });

    sidebarCollapsedFlyoutClose?.addEventListener('click', function () {
        closeCollapsedSidebarFlyout({ restoreFocus: true });
    });

    sidebarCollapsedFlyoutLinks?.addEventListener('click', function (event) {
        if (event.target.closest('a[href]')) {
            closeCollapsedSidebarFlyout();
        }
    });

    sidebarCollapsedFlyout?.addEventListener('keydown', function (event) {
        const links = Array.from(sidebarCollapsedFlyoutLinks?.querySelectorAll('a[href]') || []);
        const currentIndex = links.indexOf(document.activeElement);

        if (event.key === 'Escape') {
            event.preventDefault();
            closeCollapsedSidebarFlyout({ restoreFocus: true });
        } else if (event.key === 'ArrowDown' && links.length) {
            event.preventDefault();
            links[(currentIndex + 1) % links.length].focus();
        } else if (event.key === 'ArrowUp' && links.length) {
            event.preventDefault();
            links[(currentIndex - 1 + links.length) % links.length].focus();
        }
    });

    sidebar.querySelector('.sidebar-navigation')?.addEventListener('scroll', function () {
        closeCollapsedSidebarFlyout();
    }, { passive: true });

    function syncFavoriteActiveStates() {
        sidebar.querySelectorAll('[data-sidebar-favorite-item]').forEach(function (favoriteRow) {
            const sourceRow = Array.from(sidebar.querySelectorAll('[data-sidebar-source-item]'))
                .find(row => row.dataset.sidebarSourceItem === favoriteRow.dataset.sidebarFavoriteItem);
            const sourceLink = sourceRow?.matches('a.nav-link')
                ? sourceRow
                : sourceRow?.querySelector('a.nav-link');
            const favoriteLink = favoriteRow.querySelector('a.nav-link');
            if (favoriteLink) {
                favoriteLink.classList.toggle('active', Boolean(sourceLink?.classList.contains('active')));
            }
        });
    }

    function updateFavoriteFormState(form, pinned) {
        form.dataset.favoriteState = pinned ? 'pinned' : 'unpinned';
        const actionInput = form.querySelector('[data-sidebar-favorite-action]');
        const button = form.querySelector('[data-sidebar-favorite-accessible-action]');
        const label = form.dataset.favoriteLabel || 'element';

        if (actionInput) {
            actionInput.value = pinned ? 'remove' : 'add';
        }
        if (button) {
            const accessibleLabel = pinned
                ? `Usuń ${label} z Favorites`
                : `Dodaj ${label} do Favorites`;
            button.textContent = accessibleLabel;
        }
    }

    function replaceFavoritesContent(html) {
        const template = document.createElement('template');
        template.innerHTML = (html || '').trim();
        const nextContent = template.content.querySelector('[data-sidebar-favorites-content]');
        const currentContent = sidebar.querySelector('[data-sidebar-favorites-content]');
        if (!nextContent || !currentContent) {
            return false;
        }

        currentContent.replaceWith(nextContent);
        window.AncoreIcons?.render(nextContent);
        syncSidebarFavoritesVisibility();
        return true;
    }

    function favoriteRows() {
        return Array.from(sidebar.querySelectorAll('[data-sidebar-favorites-list] > [data-sidebar-favorite-item]'));
    }

    function favoriteOrder() {
        return favoriteRows().map(row => row.dataset.sidebarFavoriteItem);
    }

    function restoreFavoriteOrder(itemOrder) {
        const list = sidebar.querySelector('[data-sidebar-favorites-list]');
        if (!list || !Array.isArray(itemOrder)) return;

        const rowsByKey = new Map(favoriteRows().map(row => [row.dataset.sidebarFavoriteItem, row]));
        itemOrder.forEach(function (itemKey) {
            const row = rowsByKey.get(itemKey);
            if (row) list.appendChild(row);
        });
    }

    let favoriteReorderPlaceholder = null;

    function beginFavoriteReorder(row) {
        const list = sidebar.querySelector('[data-sidebar-favorites-list]');
        if (!list || !row || favoriteReorderPlaceholder) return;

        favoriteReorderPlaceholder = document.createElement('div');
        favoriteReorderPlaceholder.className = 'sidebar-favorite-placeholder';
        favoriteReorderPlaceholder.setAttribute('aria-hidden', 'true');
        row.after(favoriteReorderPlaceholder);
        row.classList.add('is-reordering');
    }

    function positionFavoritePlaceholder(clientY) {
        const list = sidebar.querySelector('[data-sidebar-favorites-list]');
        const draggedRow = sidebar.querySelector('[data-sidebar-favorite-item].is-dragging');
        if (!list || !draggedRow || !favoriteReorderPlaceholder) return;

        const nextRow = favoriteRows()
            .filter(row => row !== draggedRow)
            .find(row => clientY < row.getBoundingClientRect().top + row.getBoundingClientRect().height / 2);
        list.insertBefore(favoriteReorderPlaceholder, nextRow || null);
    }

    function commitFavoriteReorder() {
        const list = sidebar.querySelector('[data-sidebar-favorites-list]');
        const draggedRow = sidebar.querySelector('[data-sidebar-favorite-item].is-dragging');
        if (!list || !draggedRow || !favoriteReorderPlaceholder) return false;

        list.insertBefore(draggedRow, favoriteReorderPlaceholder);
        favoriteReorderPlaceholder.remove();
        favoriteReorderPlaceholder = null;
        draggedRow.classList.remove('is-reordering');
        return true;
    }

    let favoriteOrderSaveQueue = Promise.resolve();
    let favoriteOrderSaveVersion = 0;

    function saveFavoriteOrder(originalOrder) {
        const form = sidebar.querySelector('[data-sidebar-favorites-reorder-form]');
        const orderInput = form?.querySelector('[data-sidebar-favorites-order]');
        const orderStatus = sidebar.querySelector('[data-sidebar-favorites-order-status]');
        if (!form || !orderInput) {
            restoreFavoriteOrder(originalOrder);
            return;
        }

        const nextOrder = favoriteOrder();
        if (JSON.stringify(nextOrder) === JSON.stringify(originalOrder)) return;

        orderInput.value = JSON.stringify(nextOrder);
        if (typeof window.fetch !== 'function' || typeof window.FormData !== 'function') {
            form.submit();
            return;
        }

        const saveVersion = ++favoriteOrderSaveVersion;
        const formData = new FormData(form);
        formData.set('item_order', JSON.stringify(nextOrder));
        favoriteOrderSaveQueue = favoriteOrderSaveQueue
            .catch(function () {})
            .then(async function () {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    credentials: 'same-origin',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json',
                    },
                });
                const payload = await response.json();
                if (!response.ok || payload.status !== 'success') {
                    throw new Error(payload.message || 'Nie udało się zapisać kolejności Favorites.');
                }
                if (saveVersion === favoriteOrderSaveVersion && orderStatus) {
                    orderStatus.textContent = 'Kolejność Favorites została zapisana.';
                }
            })
            .catch(function (error) {
                if (saveVersion === favoriteOrderSaveVersion) {
                    restoreFavoriteOrder(originalOrder);
                    if (orderStatus) orderStatus.textContent = error.message;
                }
            });
    }

    sidebar.addEventListener('submit', async function (event) {
        const form = event.target.closest?.('[data-sidebar-favorite-form]');
        if (!form || typeof window.fetch !== 'function' || typeof window.FormData !== 'function') {
            return;
        }

        event.preventDefault();
        const button = form.querySelector('[data-sidebar-favorite-accessible-action]');
        if (button?.disabled) {
            return;
        }

        if (button) {
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
        }

        try {
            const response = await fetch(form.action, {
                method: 'POST',
                body: new FormData(form),
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json',
                },
            });
            const payload = await response.json();
            if (!response.ok || payload.status !== 'success' || !replaceFavoritesContent(payload.html)) {
                throw new Error(payload.message || 'Nie udało się zmienić Favorites.');
            }

            sidebar.querySelectorAll('[data-sidebar-favorite-form]').forEach(function (favoriteForm) {
                if (favoriteForm.dataset.favoriteKey === payload.item_key) {
                    updateFavoriteFormState(favoriteForm, payload.is_favorite);
                }
            });
            syncFavoriteActiveStates();
        } catch (error) {
            form.submit();
        } finally {
            if (button?.isConnected) {
                button.disabled = false;
                button.removeAttribute('aria-busy');
            }
        }
    });

    let draggedSidebarItem = null;
    let pointerSidebarDrag = null;
    let suppressSidebarDragClick = false;
    let sidebarDragPreview = null;

    function removeSidebarDragPreview() {
        sidebarDragPreview?.remove();
        sidebarDragPreview = null;
    }

    function createSidebarDragPreview(row) {
        removeSidebarDragPreview();

        const visualRow = row.matches('a.nav-link')
            ? row
            : row.querySelector('a.nav-link');
        if (!visualRow) return null;

        const preview = document.createElement('div');
        preview.className = 'sidebar-drag-preview';
        preview.setAttribute('aria-hidden', 'true');

        const icon = visualRow.querySelector('.nav-icon, .sidebar-subnav-icon, .sidebar-favorite-icon');
        if (icon) {
            const iconClone = icon.cloneNode(true);
            iconClone.classList.add('sidebar-drag-preview__icon');
            preview.appendChild(iconClone);
        }

        const label = visualRow.querySelector('.nav-label')
            || visualRow.querySelector('span:last-child');
        const labelText = label?.textContent?.trim() || visualRow.textContent.trim();
        const labelElement = document.createElement('span');
        labelElement.className = 'sidebar-drag-preview__label';
        labelElement.textContent = labelText;
        preview.appendChild(labelElement);

        const rowWidth = row.getBoundingClientRect().width;
        preview.style.width = `${Math.min(Math.max(rowWidth, 160), 280)}px`;
        document.body.appendChild(preview);
        sidebarDragPreview = preview;
        return preview;
    }

    function moveSidebarDragPreview(x, y) {
        if (!sidebarDragPreview) return;

        const offset = 12;
        const edgeGap = 8;
        const previewRect = sidebarDragPreview.getBoundingClientRect();
        const left = Math.max(
            edgeGap,
            Math.min(x + offset, window.innerWidth - previewRect.width - edgeGap)
        );
        const top = Math.max(
            edgeGap,
            Math.min(y + offset, window.innerHeight - previewRect.height - edgeGap)
        );
        sidebarDragPreview.style.transform = `translate3d(${left}px, ${top}px, 0)`;
    }

    function clearSidebarDragState(options) {
        if (options?.restoreFavoriteOrder && draggedSidebarItem?.origin === 'favorites') {
            restoreFavoriteOrder(draggedSidebarItem.originalOrder);
        }
        sidebar.querySelectorAll('.is-dragging').forEach(item => item.classList.remove('is-dragging'));
        sidebar.querySelectorAll('.is-reordering').forEach(item => item.classList.remove('is-reordering'));
        favoriteReorderPlaceholder?.remove();
        favoriteReorderPlaceholder = null;
        sidebarFavoritesDropzone?.classList.remove('is-drag-over');
        sidebarFavoritesRemoveDropzone?.classList.remove('is-drag-over');
        sidebar.classList.remove('is-dragging-from-workspace', 'is-dragging-from-favorites');
        removeSidebarDragPreview();
        draggedSidebarItem = null;
    }

    function favoriteFormForItem(itemKey, origin) {
        if (origin === 'favorites') {
            const row = Array.from(sidebar.querySelectorAll('[data-sidebar-favorite-item]'))
                .find(candidate => candidate.dataset.sidebarFavoriteItem === itemKey);
            return row?.querySelector('[data-sidebar-favorite-form]') || null;
        }

        return Array.from(sidebar.querySelectorAll('[data-sidebar-favorite-form]')).find(form => (
            form.dataset.favoriteKey === itemKey && form.dataset.favoriteState === 'unpinned'
        )) || null;
    }

    function submitDraggedFavorite(action) {
        if (!draggedSidebarItem) return;

        const expectedOrigin = action === 'add' ? 'workspace' : 'favorites';
        if (draggedSidebarItem.origin !== expectedOrigin) return;

        const form = favoriteFormForItem(draggedSidebarItem.key, expectedOrigin);
        const expectedState = action === 'add' ? 'unpinned' : 'pinned';
        if (!form || form.dataset.favoriteState !== expectedState) return;

        const actionInput = form.querySelector('[data-sidebar-favorite-action]');
        if (actionInput) actionInput.value = action;
        form.requestSubmit();
    }

    function sidebarDropzoneAt(x, y) {
        const target = document.elementFromPoint(x, y);
        if (!(target instanceof Element)) return null;

        return target.closest('[data-sidebar-favorites-dropzone], [data-sidebar-favorites-remove-dropzone]');
    }

    function updateSidebarDropzoneHighlight(dropzone) {
        sidebarFavoritesDropzone?.classList.toggle(
            'is-drag-over',
            dropzone === sidebarFavoritesDropzone && draggedSidebarItem?.origin === 'workspace'
        );
        sidebarFavoritesRemoveDropzone?.classList.toggle(
            'is-drag-over',
            dropzone === sidebarFavoritesRemoveDropzone && draggedSidebarItem?.origin === 'favorites'
        );
    }

    function restorePointerDragRow(pointerDrag) {
        if (!pointerDrag?.dragElement) return;

        pointerDrag.dragElement.draggable = true;
        if (pointerDrag.dragElement.hasPointerCapture?.(pointerDrag.pointerId)) {
            pointerDrag.dragElement.releasePointerCapture(pointerDrag.pointerId);
        }
    }

    sidebar.addEventListener('dragstart', function (event) {
        const row = event.target.closest?.('[data-sidebar-source-item], [data-sidebar-favorite-item]');
        if (!row || !event.dataTransfer) return;

        const fromFavorites = row.hasAttribute('data-sidebar-favorite-item');
        const itemKey = fromFavorites
            ? row.dataset.sidebarFavoriteItem
            : row.dataset.sidebarSourceItem;
        if (!itemKey) return;

        draggedSidebarItem = {
            key: itemKey,
            origin: fromFavorites ? 'favorites' : 'workspace',
            originalOrder: fromFavorites ? favoriteOrder() : null,
        };
        const preview = createSidebarDragPreview(row);
        if (preview) {
            preview.classList.add('sidebar-drag-preview--native');
            event.dataTransfer.setDragImage(preview, 18, 18);
        }
        if (fromFavorites) beginFavoriteReorder(row);
        row.classList.add('is-dragging');
        sidebar.classList.add(fromFavorites ? 'is-dragging-from-favorites' : 'is-dragging-from-workspace');
        event.dataTransfer.effectAllowed = fromFavorites ? 'move' : 'copy';
        event.dataTransfer.setData('text/plain', itemKey);
    });


    sidebar.addEventListener('dragend', function () {
        clearSidebarDragState({restoreFavoriteOrder: true});
    });

    sidebarFavoritesDropzone?.addEventListener('dragover', function (event) {
        if (!draggedSidebarItem) return;
        event.preventDefault();
        if (draggedSidebarItem.origin === 'favorites') {
            event.dataTransfer.dropEffect = 'move';
            positionFavoritePlaceholder(event.clientY);
        } else {
            event.dataTransfer.dropEffect = 'copy';
            sidebarFavoritesDropzone.classList.add('is-drag-over');
        }
    });

    sidebarFavoritesDropzone?.addEventListener('dragleave', function (event) {
        if (event.relatedTarget instanceof Node && sidebarFavoritesDropzone.contains(event.relatedTarget)) return;
        sidebarFavoritesDropzone.classList.remove('is-drag-over');
    });

    sidebarFavoritesDropzone?.addEventListener('drop', function (event) {
        if (!draggedSidebarItem) return;
        event.preventDefault();
        if (draggedSidebarItem.origin === 'favorites') {
            positionFavoritePlaceholder(event.clientY);
            if (commitFavoriteReorder()) {
                saveFavoriteOrder(draggedSidebarItem.originalOrder);
            }
        } else {
            submitDraggedFavorite('add');
        }
        clearSidebarDragState();
    });

    sidebarFavoritesRemoveDropzone?.addEventListener('dragover', function (event) {
        if (draggedSidebarItem?.origin !== 'favorites') return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        sidebarFavoritesRemoveDropzone.classList.add('is-drag-over');
    });

    sidebarFavoritesRemoveDropzone?.addEventListener('dragleave', function (event) {
        if (event.relatedTarget instanceof Node && sidebarFavoritesRemoveDropzone.contains(event.relatedTarget)) return;
        sidebarFavoritesRemoveDropzone.classList.remove('is-drag-over');
    });

    sidebarFavoritesRemoveDropzone?.addEventListener('drop', function (event) {
        if (draggedSidebarItem?.origin !== 'favorites') return;
        event.preventDefault();
        submitDraggedFavorite('remove');
        clearSidebarDragState();
    });

    sidebar.addEventListener('pointerdown', function (event) {
        if (!event.isPrimary || event.button !== 0) return;

        const row = event.target.closest?.('[data-sidebar-source-item], [data-sidebar-favorite-item]');
        if (!row || event.target.closest?.('button, input, form')) return;

        const fromFavorites = row.hasAttribute('data-sidebar-favorite-item');
        const itemKey = fromFavorites
            ? row.dataset.sidebarFavoriteItem
            : row.dataset.sidebarSourceItem;
        if (!itemKey) return;

        pointerSidebarDrag = {
            pointerId: event.pointerId,
            startX: event.clientX,
            startY: event.clientY,
            row: row,
            dragElement: row,
            key: itemKey,
            origin: fromFavorites ? 'favorites' : 'workspace',
            originalOrder: fromFavorites ? favoriteOrder() : null,
            active: false,
        };

        // Pointer-driven dragging works consistently for mouse, pen and touch.
        // Native dragging stays available for non-pointer input.
        pointerSidebarDrag.dragElement.draggable = false;
    });

    sidebar.addEventListener('pointermove', function (event) {
        const pointerDrag = pointerSidebarDrag;
        if (!pointerDrag || event.pointerId !== pointerDrag.pointerId) return;

        if (!pointerDrag.active) {
            const distance = Math.hypot(
                event.clientX - pointerDrag.startX,
                event.clientY - pointerDrag.startY
            );
            if (distance < 6) return;

            pointerDrag.active = true;
            draggedSidebarItem = {
                key: pointerDrag.key,
                origin: pointerDrag.origin,
                originalOrder: pointerDrag.originalOrder,
            };
            createSidebarDragPreview(pointerDrag.row);
            if (pointerDrag.origin === 'favorites') beginFavoriteReorder(pointerDrag.row);
            pointerDrag.row.classList.add('is-dragging');
            pointerDrag.dragElement.setPointerCapture?.(event.pointerId);
            sidebar.classList.add(
                pointerDrag.origin === 'favorites'
                    ? 'is-dragging-from-favorites'
                    : 'is-dragging-from-workspace'
            );
        }

        event.preventDefault();
        moveSidebarDragPreview(event.clientX, event.clientY);
        const dropzone = sidebarDropzoneAt(event.clientX, event.clientY);
        if (dropzone === sidebarFavoritesDropzone && pointerDrag.origin === 'favorites') {
            positionFavoritePlaceholder(event.clientY);
        }
        updateSidebarDropzoneHighlight(dropzone);
    });

    sidebar.addEventListener('pointerup', function (event) {
        const pointerDrag = pointerSidebarDrag;
        if (!pointerDrag || event.pointerId !== pointerDrag.pointerId) return;

        pointerSidebarDrag = null;
        restorePointerDragRow(pointerDrag);
        if (!pointerDrag.active) return;

        event.preventDefault();
        suppressSidebarDragClick = true;

        const dropzone = sidebarDropzoneAt(event.clientX, event.clientY);
        if (dropzone === sidebarFavoritesDropzone && pointerDrag.origin === 'workspace') {
            submitDraggedFavorite('add');
        } else if (dropzone === sidebarFavoritesDropzone && pointerDrag.origin === 'favorites') {
            positionFavoritePlaceholder(event.clientY);
            if (commitFavoriteReorder()) {
                saveFavoriteOrder(pointerDrag.originalOrder);
            }
        } else if (dropzone === sidebarFavoritesRemoveDropzone && pointerDrag.origin === 'favorites') {
            submitDraggedFavorite('remove');
        } else if (pointerDrag.origin === 'favorites') {
            restoreFavoriteOrder(pointerDrag.originalOrder);
        }

        clearSidebarDragState();
        window.setTimeout(function () {
            suppressSidebarDragClick = false;
        }, 0);
    });

    sidebar.addEventListener('pointercancel', function (event) {
        const pointerDrag = pointerSidebarDrag;
        if (!pointerDrag || event.pointerId !== pointerDrag.pointerId) return;

        pointerSidebarDrag = null;
        restorePointerDragRow(pointerDrag);
        clearSidebarDragState();
    });

    sidebar.addEventListener('click', function (event) {
        if (!suppressSidebarDragClick) return;

        suppressSidebarDragClick = false;
        event.preventDefault();
        event.stopImmediatePropagation();
    }, true);

    sidebar.addEventListener('keydown', function (event) {
        if (!event.altKey || !['ArrowUp', 'ArrowDown'].includes(event.key)) return;

        const link = event.target.closest?.('[data-sidebar-favorite-item] .sidebar-favorite-link');
        const row = link?.closest('[data-sidebar-favorite-item]');
        const list = row?.closest('[data-sidebar-favorites-list]');
        if (!link || !row || !list) return;

        const sibling = event.key === 'ArrowUp' ? row.previousElementSibling : row.nextElementSibling;
        if (!sibling?.matches('[data-sidebar-favorite-item]')) return;

        event.preventDefault();
        const originalOrder = favoriteOrder();
        if (event.key === 'ArrowUp') {
            list.insertBefore(row, sibling);
        } else {
            list.insertBefore(sibling, row);
        }
        saveFavoriteOrder(originalOrder);
        link.focus();
    });

    syncFavoriteActiveStates();

    function setSecondaryMenuCollapsed(collapsed) {
        document.documentElement.classList.toggle('secondary-menu-collapsed', collapsed);
        document.body.classList.toggle('secondary-menu-collapsed', collapsed);

        secondaryMenu?.setAttribute('aria-hidden', collapsed ? 'true' : 'false');

        if (secondaryMenuToggle) {
            secondaryMenuToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
            secondaryMenuToggle.setAttribute('aria-label', collapsed ? 'Rozwiń drugie menu' : 'Zwiń drugie menu');
            secondaryMenuToggle.setAttribute('title', collapsed ? 'Rozwiń drugie menu' : 'Zwiń drugie menu');
        }
    }

    function getSecondaryMenuWidth() {
        if (!secondaryMenu) {
            return 0;
        }

        return secondaryMenu.offsetWidth || secondaryMenu.getBoundingClientRect().width;
    }

    function getSidebarWidth() {
        return sidebar.offsetWidth || sidebar.getBoundingClientRect().width;
    }

    function getAppViewportWidth() {
        return window.innerWidth;
    }

    function getSecondaryMenuBounds() {
        const min = SECONDARY_MENU_MIN_WIDTH;
        const availableWidth = getAppViewportWidth() - getSidebarWidth();
        const max = Math.min(
            SECONDARY_MENU_MAX_WIDTH,
            Math.max(
                min,
                isOverlayMode() ? availableWidth : availableWidth - SECONDARY_MENU_CONTENT_MIN_WIDTH
            )
        );

        return { min, max };
    }

    function clampSecondaryMenuWidth(width) {
        const bounds = getSecondaryMenuBounds();

        return Math.min(bounds.max, Math.max(bounds.min, width));
    }

    function updateSecondaryMenuResizeA11y(width) {
        if (!secondaryMenuResizer) {
            return;
        }

        const bounds = getSecondaryMenuBounds();
        secondaryMenuResizer.setAttribute('aria-valuemin', String(bounds.min));
        secondaryMenuResizer.setAttribute('aria-valuemax', String(bounds.max));
        secondaryMenuResizer.setAttribute('aria-valuenow', String(Math.round(width)));
    }

    function setSecondaryMenuWidth(width, persist) {
        const nextWidth = clampSecondaryMenuWidth(width);
        document.documentElement.style.setProperty('--secondary-menu-width', nextWidth + 'px');
        updateSecondaryMenuResizeA11y(nextWidth);

        if (persist) {
            localStorage.setItem('secondaryMenuWidth', String(Math.round(nextWidth)));
        }
    }

    if (secondaryMenu && secondaryMenuToggle) {
        const savedSecondaryMenuState = localStorage.getItem('secondaryMenuCollapsed');
        setSecondaryMenuCollapsed(savedSecondaryMenuState === 'true');

        secondaryMenuToggle.addEventListener('click', function () {
            const collapsed = !document.body.classList.contains('secondary-menu-collapsed');
            document.body.classList.add('secondary-menu-toggling');
            setSecondaryMenuCollapsed(collapsed);
            localStorage.setItem('secondaryMenuCollapsed', collapsed ? 'true' : 'false');
            window.setTimeout(function () {
                document.body.classList.remove('secondary-menu-toggling');
            }, 220);
        });
    }

    if (secondaryMenu && secondaryMenuResizer) {
        const savedSecondaryMenuWidth = Number(localStorage.getItem('secondaryMenuWidth'));
        if (Number.isFinite(savedSecondaryMenuWidth) && savedSecondaryMenuWidth > 0) {
            setSecondaryMenuWidth(savedSecondaryMenuWidth, false);
        } else {
            updateSecondaryMenuResizeA11y(getSecondaryMenuWidth());
        }

        secondaryMenuResizer.addEventListener('pointerdown', function (e) {
            if (isOverlayMode() || document.body.classList.contains('secondary-menu-collapsed')) {
                return;
            }

            e.preventDefault();
            secondaryMenuResizer.setPointerCapture(e.pointerId);
            secondaryMenuResizeState = {
                pointerId: e.pointerId,
                startX: e.clientX,
                startWidth: getSecondaryMenuWidth(),
            };
            document.body.classList.add('secondary-menu-resizing');
        });

        window.addEventListener('pointermove', function (e) {
            if (!secondaryMenuResizeState || e.pointerId !== secondaryMenuResizeState.pointerId) {
                return;
            }

            const deltaX = e.clientX - secondaryMenuResizeState.startX;
            setSecondaryMenuWidth(secondaryMenuResizeState.startWidth + deltaX, false);
        });

        function finishSecondaryMenuResize(e) {
            if (!secondaryMenuResizeState || e.pointerId !== secondaryMenuResizeState.pointerId) {
                return;
            }

            if (secondaryMenuResizer.hasPointerCapture(e.pointerId)) {
                secondaryMenuResizer.releasePointerCapture(e.pointerId);
            }

            document.body.classList.remove('secondary-menu-resizing');
            secondaryMenuResizeState = null;
            setSecondaryMenuWidth(getSecondaryMenuWidth(), true);
        }

        window.addEventListener('pointerup', finishSecondaryMenuResize);
        window.addEventListener('pointercancel', finishSecondaryMenuResize);

        secondaryMenuResizer.addEventListener('keydown', function (e) {
            if (document.body.classList.contains('secondary-menu-collapsed')) {
                return;
            }

            if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') {
                return;
            }

            e.preventDefault();
            setSecondaryMenuWidth(getSecondaryMenuWidth() + (e.key === 'ArrowRight' ? 16 : -16), true);
        });

        window.addEventListener('resize', function () {
            if (!isOverlayMode() && !document.body.classList.contains('secondary-menu-collapsed')) {
                setSecondaryMenuWidth(getSecondaryMenuWidth(), false);
            }
        });
    }

    if (toggle) {
        toggle.addEventListener('click', function () {
            setOpen(!document.body.classList.contains('sidebar-open'));
        });
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeSidebar);
    }

    sidebar.querySelectorAll('a.nav-link, button.nav-link:not([data-sidebar-group-toggle]), a.sidebar-view-switcher__item').forEach(function (link) {
        link.addEventListener('click', function () {
            setSidebarSearchOpen(false);
            if (isOverlayMode()) {
                closeSidebar();
            }
        });
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeCollapsedSidebarFlyout();
            setWorkspaceMenuOpen(false);
            closeSidebar();
        }
    });

    function onBreakpointChange() {
        if (!isOverlayMode()) {
            closeSidebar();
        }
        syncSidebarWidthForViewport();
        updateSidebarCollapseA11y();
    }

    window.addEventListener('resize', function () {
        if (!isOverlayMode() && !sidebarResizeState) {
            syncSidebarWidthForViewport();
        }
    });

    if (typeof MQ_MOBILE.addEventListener === 'function') {
        MQ_MOBILE.addEventListener('change', onBreakpointChange);
    } else {
        MQ_MOBILE.addListener(onBreakpointChange);
    }

    onBreakpointChange();

    function finishShellBoot() {
        document.documentElement.classList.remove('app-shell-booting');
    }

    if (typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(function () {
            window.requestAnimationFrame(finishShellBoot);
        });
    } else {
        window.setTimeout(finishShellBoot, 0);
    }
})();
