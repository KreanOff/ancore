(function () {
    const MQ_TABLET = window.matchMedia('(max-width: 1024px)');

    const sidebar = document.querySelector('.sidebar');
    const toggle = document.getElementById('sidebar-toggle');
    const backdrop = document.getElementById('sidebar-backdrop');
    const secondaryMenu = document.getElementById('secondary-menu');
    const secondaryMenuToggle = document.getElementById('secondary-menu-toggle');

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
