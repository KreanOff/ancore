(function () {
    const config = window.AncorePresence;

    if (!config || !config.pingUrl) {
        return;
    }

    const idleMs = Math.max(30, Number(config.idleSeconds) || 120) * 1000;
    const heartbeatMs = Math.max(10, Number(config.heartbeatSeconds) || 30) * 1000;
    const storageKey = 'ancore:lastActivityAt';
    let fallbackLastActivityAt = 0;
    let lastSentState = null;
    let lastPingAt = 0;
    let lastActivityWriteAt = 0;

    function now() {
        return Date.now();
    }

    function readLastActivityAt() {
        try {
            const storedValue = Number(localStorage.getItem(storageKey));
            return Number.isFinite(storedValue) && storedValue > 0 ? storedValue : fallbackLastActivityAt;
        } catch (_error) {
            return fallbackLastActivityAt;
        }
    }

    function writeLastActivityAt(value) {
        fallbackLastActivityAt = value;

        try {
            localStorage.setItem(storageKey, String(value));
        } catch (_error) {
            // Presence still works in this tab when localStorage is unavailable.
        }
    }

    function cookieValue(name) {
        return document.cookie
            .split(';')
            .map(part => part.trim())
            .find(part => part.startsWith(name + '='))
            ?.slice(name.length + 1) || '';
    }

    function csrfToken() {
        return config.csrfToken || decodeURIComponent(cookieValue('csrftoken'));
    }

    function isRecentlyActive() {
        return now() - readLastActivityAt() < idleMs;
    }

    function sendPresence(active, force) {
        const timestamp = now();

        if (!force && active === lastSentState && timestamp - lastPingAt < heartbeatMs) {
            return;
        }

        lastSentState = active;
        lastPingAt = timestamp;

        fetch(config.pingUrl, {
            method: 'POST',
            credentials: 'same-origin',
            keepalive: true,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify({ active }),
        }).catch(() => {});
    }

    function evaluatePresence(force) {
        sendPresence(isRecentlyActive(), force);
    }

    function markActivity() {
        const timestamp = now();

        if (timestamp - lastActivityWriteAt < 1000) {
            return;
        }

        lastActivityWriteAt = timestamp;
        writeLastActivityAt(timestamp);

        if (lastSentState === false) {
            sendPresence(true, true);
        }
    }

    ['pointerdown', 'keydown', 'scroll', 'touchstart', 'focus'].forEach(eventName => {
        window.addEventListener(eventName, markActivity, { passive: true });
    });

    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') {
            markActivity();
            evaluatePresence(true);
        }
    });

    markActivity();
    evaluatePresence(true);
    window.setInterval(() => evaluatePresence(false), heartbeatMs);
})();
