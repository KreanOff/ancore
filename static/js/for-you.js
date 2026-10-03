(function () {
    if (window.ancoreForYouLoaded) return;
    window.ancoreForYouLoaded = true;

    let observer;

    function disconnect() {
        observer?.disconnect();
        observer = null;
    }

    function init() {
        disconnect();
        const tabs = document.querySelector('.for-you-tabs');
        const active = tabs?.querySelector('[aria-current="page"]');
        if (!active) return;

        function revealActiveTab() {
            const start = active.offsetLeft;
            const end = start + active.offsetWidth;
            if (start < tabs.scrollLeft) {
                tabs.scrollLeft = start;
            } else if (end > tabs.scrollLeft + tabs.clientWidth) {
                tabs.scrollLeft = end - tabs.clientWidth;
            }
        }

        // Scroll only the tabs, keeping the page's vertical position and focus.
        revealActiveTab();
        observer = new ResizeObserver(revealActiveTab);
        observer.observe(tabs);
        observer.observe(active);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
    document.addEventListener('ancore:content-loaded', init);
    document.addEventListener('ancore:content-unloading', disconnect);
})();
