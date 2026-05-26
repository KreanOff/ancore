(function () {
    const MQ_TABLET = window.matchMedia('(max-width: 1024px)');

    const sidebar = document.querySelector('.sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');
    const secondaryMenu = document.getElementById('secondary-menu');
    const secondaryMenuToggle = document.getElementById('secondary-menu-toggle');
    const secondaryMenuResizer = document.getElementById('secondary-menu-resizer');
    let secondaryMenuResizeState = null;

    if (!sidebar || !toggle) {
        return;
    }

    function isOverlayMode() {
        return MQ_TABLET.matches;
    }

    function setOpen(open) {
        const on = open && isOverlayMode();
        document.body.classList.toggle('sidebar-open', on);
        sidebar.classList.toggle('sidebar--visible', on);
        toggle.setAttribute('aria-expanded', on ? 'true' : 'false');
        toggle.setAttribute('aria-label', on ? 'Zamknij menu' : 'Otwórz menu');
    }

    function closeSidebar() {
        setOpen(false);
    }

    function setSecondaryMenuCollapsed(collapsed) {
        document.body.classList.toggle('secondary-menu-collapsed', collapsed);

        if (!secondaryMenuToggle) {
            return;
        }

        secondaryMenuToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
        secondaryMenuToggle.setAttribute('aria-label', collapsed ? 'Rozwiń drugie menu' : 'Zwiń drugie menu');
        secondaryMenuToggle.setAttribute('title', collapsed ? 'Rozwiń drugie menu' : 'Zwiń drugie menu');
    }

    function getSecondaryMenuWidth() {
        if (!secondaryMenu) {
            return 0;
        }

        return secondaryMenu.getBoundingClientRect().width;
    }

    function getSidebarWidth() {
        return sidebar.getBoundingClientRect().width;
    }

    function getSecondaryMenuBounds() {
        const min = 180;
        const max = Math.max(min, window.innerWidth - getSidebarWidth() - 240);

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
        const forceSecondaryMenuOpen = Boolean(secondaryMenu.querySelector('.tasks-tracker-rail'));
        setSecondaryMenuCollapsed(forceSecondaryMenuOpen ? false : savedSecondaryMenuState === 'true');

        secondaryMenuToggle.addEventListener('click', function () {
            const collapsed = !document.body.classList.contains('secondary-menu-collapsed');
            setSecondaryMenuCollapsed(collapsed);
            localStorage.setItem('secondaryMenuCollapsed', collapsed ? 'true' : 'false');
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

            setSecondaryMenuWidth(secondaryMenuResizeState.startWidth + e.clientX - secondaryMenuResizeState.startX, false);
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

    toggle.addEventListener('click', function () {
        setOpen(!document.body.classList.contains('sidebar-open'));
    });

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
})();
