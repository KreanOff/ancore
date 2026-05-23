(function () {
    const timeEl = document.getElementById('topbar-time');

    if (!timeEl) {
        return;
    }

    const formatter = new Intl.DateTimeFormat('pl-PL', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
        timeZone: 'Europe/Warsaw',
    });

    function updateClock() {
        timeEl.textContent = formatter.format(new Date());
    }

    updateClock();
    window.setInterval(updateClock, 30000);
})();
