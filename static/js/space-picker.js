/* Shared searchable navigation for spaces and dashboards. */
(function () {
    if (window.ancoreSidebarPickerLoaded) return;
    window.ancoreSidebarPickerLoaded = true;
    document.querySelectorAll('[data-sidebar-picker]').forEach(initPicker);

    function initPicker(panel) {
        const group = panel.dataset.sidebarPicker;
        const toggleSelector = `[data-sidebar-picker-toggle="${group}"]`;
        const input = panel.querySelector('[data-sidebar-picker-input]');
        const form = panel.querySelector('[data-sidebar-picker-form]');
        const results = panel.querySelector('[data-sidebar-picker-results]');
        const status = panel.querySelector('[data-sidebar-picker-status]');
        const directory = panel.querySelector('[data-sidebar-picker-directory]');
        let returnFocus, anchor, controller, timer;
        let requestVersion = 0;
        const isOpen = () => panel.matches(':popover-open');

        function cancelSearch() {
            window.clearTimeout(timer);
            controller?.abort();
            requestVersion += 1;
            results.removeAttribute('aria-busy');
        }

        function position() {
            if (!isOpen()) return;
            const rect = panel.getBoundingClientRect();
            const scale = rect.width / panel.offsetWidth || 1;
            const margin = 8;
            const mobile = window.matchMedia('(max-width: 767px)').matches;
            const sidebarRight = document.querySelector('.sidebar')?.getBoundingClientRect().right || 0;
            const left = mobile ? margin : Math.min(
                Math.max(anchor.right, sidebarRight) + margin,
                window.innerWidth - rect.width - margin
            );
            const top = Math.min(mobile ? anchor.bottom + margin : anchor.top, window.innerHeight - rect.height - margin);
            panel.style.left = `${Math.max(margin, left) / scale}px`;
            panel.style.top = `${Math.max(margin, top) / scale}px`;
        }

        function message(text) {
            status.textContent = text;
            status.hidden = !text;
        }

        function updateDirectory() {
            const url = new URL(panel.dataset.directoryUrl, window.location.href);
            const query = input.value.trim();
            if (query) url.searchParams.set('q', query);
            directory.href = url.href;
            form.action = panel.dataset.directoryUrl;
        }

        function close(restoreFocus = false) {
            if (!isOpen()) return;
            panel.hidePopover();
            if (restoreFocus && returnFocus?.isConnected) returnFocus.focus({ preventScroll: true });
        }

        async function search() {
            cancelSearch();
            const query = input.value.trim();
            updateDirectory();
            results.replaceChildren();
            results.hidden = true;
            if (!query) {
                message('');
                position();
                return;
            }
            const version = requestVersion;
            controller = new AbortController();
            const url = new URL(panel.dataset.searchUrl, window.location.href);
            url.searchParams.set('q', query);
            message('Wyszukiwanie…');
            results.setAttribute('aria-busy', 'true');
            position();
            try {
                const response = await fetch(url, {
                    credentials: 'same-origin',
                    headers: { Accept: 'application/json' },
                    signal: AbortSignal.any([controller.signal, AbortSignal.timeout(10000)]),
                });
                if (!response.ok || response.redirected) throw new Error('Search failed');
                const data = await response.json();
                if (version !== requestVersion || !isOpen()) return;
                results.innerHTML = data.html;
                results.hidden = !data.count;
                message(data.count ? '' : panel.dataset.emptyMessage);
                window.AncoreIcons?.render(results);
            } catch (error) {
                if (version !== requestVersion || !isOpen()) return;
                message(panel.dataset.errorMessage);
            } finally {
                if (version === requestVersion) {
                    results.removeAttribute('aria-busy');
                    position();
                }
            }
        }

        function open(button) {
            anchor = button.getBoundingClientRect();
            returnFocus = button.closest('[data-sidebar-collapsed-flyout]')
                ? document.querySelector(`[data-sidebar-group="${group}"] [data-sidebar-group-toggle]`) : button;
            window.dispatchEvent(new CustomEvent('ancore:sidebar-picker-open'));
            input.value = '';
            results.replaceChildren();
            results.hidden = true;
            message('');
            updateDirectory();
            panel.showPopover({ source: returnFocus });
            position();
            input.focus({ preventScroll: true });
        }

        document.addEventListener('click', event => {
            const button = event.target.closest(toggleSelector);
            if (!button) return;
            event.preventDefault();
            if (isOpen()) close(true);
            else open(button);
        });
        panel.addEventListener('beforetoggle', event => {
            const expanded = event.newState === 'open';
            document.querySelectorAll(toggleSelector).forEach(button => {
                button.setAttribute('aria-expanded', String(expanded));
            });
            if (!expanded) cancelSearch();
        });
        panel.querySelector('[data-sidebar-picker-close]').addEventListener('click', () => close(true));
        input.addEventListener('input', () => {
            cancelSearch();
            updateDirectory();
            results.replaceChildren();
            results.hidden = true;
            message(input.value.trim() ? 'Wyszukiwanie…' : '');
            position();
            timer = window.setTimeout(search, 200);
        });
        form.addEventListener('submit', event => {
            event.preventDefault();
            directory.click();
        });
        panel.addEventListener('click', event => {
            if (event.target.closest('a[href]')) {
                close();
                window.dispatchEvent(new CustomEvent('ancore:sidebar-picker-navigate'));
            }
        });
        panel.addEventListener('keydown', event => {
            if (event.key === 'Escape') {
                event.preventDefault();
                event.stopPropagation();
                close(true);
            } else if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
                const items = [input, ...results.querySelectorAll('a[href]'), directory];
                const current = items.indexOf(document.activeElement);
                const step = event.key === 'ArrowDown' ? 1 : -1;
                event.preventDefault();
                items[(current + step + items.length) % items.length].focus();
            }
        });
        panel.addEventListener('focusout', () => {
            window.setTimeout(() => {
                if (isOpen() && document.activeElement !== returnFocus && !panel.contains(document.activeElement)) close();
            }, 0);
        });
        window.addEventListener('ancore:sidebar-picker-open', () => close());
        window.addEventListener('resize', () => close());
        document.querySelector('.sidebar-navigation')?.addEventListener('scroll', () => close(), { passive: true });
        ['ancore:global-search-open', 'ancore:notifications-open', 'ancore:workspace-menu-open', 'ancore:sidebar-toggle'].forEach(name => {
            window.addEventListener(name, () => close());
        });
        document.addEventListener('ancore:content-unloading', () => close());
        document.addEventListener('ancore:content-loaded', () => {
            close();
            input.value = '';
            updateDirectory();
        });
    }
})();
