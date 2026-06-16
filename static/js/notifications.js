// Notifications System
(function () {
    const DEFAULT_DURATION = 5000;

    function getNotificationsContainer() {
        let container = document.querySelector('.notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        return container;
    }

    function removeContainerIfEmpty(container) {
        if (container && container.children.length === 0) {
            container.remove();
        }
    }

    function hideNotification(notification) {
        if (!notification || notification.dataset.notificationHiding === 'true') return;
        notification.dataset.notificationHiding = 'true';
        notification.classList.add('hiding');

        setTimeout(() => {
            const container = notification.closest('.notifications-container');
            notification.remove();
            removeContainerIfEmpty(container);
        }, 300);
    }

    function showNotification(message, type = 'info', options = {}) {
        if (!message) return null;

        const container = getNotificationsContainer();
        if (options.dedupeKey) {
            container.querySelectorAll(`[data-notification-key="${options.dedupeKey}"]`).forEach(hideNotification);
        }

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.setAttribute('role', type === 'error' ? 'alert' : 'status');
        notification.setAttribute('aria-live', type === 'error' ? 'assertive' : 'polite');

        if (options.dedupeKey) {
            notification.dataset.notificationKey = options.dedupeKey;
        }

        container.appendChild(notification);

        const duration = Number.isFinite(options.duration) ? options.duration : DEFAULT_DURATION;
        if (duration > 0) {
            setTimeout(() => hideNotification(notification), duration);
        }

        return notification;
    }

    function initNotifications() {
        const notifications = document.querySelectorAll('.notification');

        notifications.forEach((notification, index) => {
            if (notification.dataset.notificationInitialized === 'true') return;
            notification.dataset.notificationInitialized = 'true';
            notification.setAttribute('role', notification.classList.contains('error') ? 'alert' : 'status');
            notification.setAttribute('aria-live', notification.classList.contains('error') ? 'assertive' : 'polite');

            setTimeout(() => {
                hideNotification(notification);
            }, DEFAULT_DURATION + (index * 500));
        });
    }

    window.showNotification = showNotification;
    window.hideNotification = hideNotification;
    window.closeNotification = hideNotification;

    document.addEventListener('DOMContentLoaded', initNotifications);
    document.addEventListener('ancore:content-loaded', initNotifications);
})();
