// Notifications System
document.addEventListener('DOMContentLoaded', function() {
    const notifications = document.querySelectorAll('.notification');
    
    notifications.forEach((notification, index) => {
        // Auto-hide notification after 5 seconds
        setTimeout(() => {
            hideNotification(notification);
        }, 5000 + (index * 500)); // Stagger multiple notifications
    });
});

function hideNotification(notification) {
    notification.classList.add('hiding');
    
    setTimeout(() => {
        notification.remove();
        
        // Remove container if no more notifications
        const container = document.querySelector('.notifications-container');
        if (container && container.children.length === 0) {
            container.remove();
        }
    }, 300);
}

// Manual close function (can be used for close buttons)
function closeNotification(notification) {
    hideNotification(notification);
}
