(function () {
    const MQ_TABLET = window.matchMedia('(max-width: 1024px)');
    const SECONDARY_MENU_MIN_WIDTH = 230;
    const SECONDARY_MENU_MAX_WIDTH = 500;
    const SECONDARY_MENU_CONTENT_MIN_WIDTH = 240;

    const sidebar = document.querySelector('.sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');
    const secondaryMenu = document.getElementById('secondary-menu');
    const secondaryMenuToggle = document.getElementById('secondary-menu-toggle');
    const secondaryMenuResizer = document.getElementById('secondary-menu-resizer');
    const loadingOverlay = document.getElementById('app-loading-overlay');
    const root = document.documentElement;
    let secondaryMenuResizeState = null;
    let pageLoadingTimer = null;
    let pageLoadingFallbackTimer = null;

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

        window.setTimeout(function () {
            if (!e.defaultPrevented) {
                requestPageLoading();
            }
        }, 0);
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

    window.addEventListener('beforeunload', showPageLoading);
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
        return;
    }

    function isOverlayMode() {
        return MQ_TABLET.matches;
    }

    function setOpen(open) {
        const on = open && isOverlayMode();
        document.body.classList.toggle('sidebar-open', on);
        sidebar.classList.toggle('sidebar--visible', on);
        if (toggle) {
            toggle.setAttribute('aria-expanded', on ? 'true' : 'false');
            toggle.setAttribute('aria-label', on ? 'Zamknij menu' : 'Otwórz menu');
        }
    }

    function closeSidebar() {
        setOpen(false);
    }

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

    sidebar.querySelectorAll('.nav-link').forEach(function (link) {
        link.addEventListener('click', function () {
            if (isOverlayMode()) {
                closeSidebar();
            }
        });
    });

    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') {
            closeSidebar();
        }
    });

    function onBreakpointChange() {
        if (!isOverlayMode()) {
            closeSidebar();
        }
    }

    if (typeof MQ_TABLET.addEventListener === 'function') {
        MQ_TABLET.addEventListener('change', onBreakpointChange);
    } else {
        MQ_TABLET.addListener(onBreakpointChange);
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
