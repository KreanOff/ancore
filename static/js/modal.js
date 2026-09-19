if (document.querySelector('.tasks-page')) {
    document.body.classList.add('tasks-ui');
}

/**
 * Universal Confirmation Modal
 */
window.escapeHtmlForModal = function (value) {
    return String(value ?? '').replace(/[&<>"']/g, (character) => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    })[character]);
};

window.showConfirmModal = function (options) {
    const {
        title = 'Potwierdzenie',
        message = 'Czy na pewno chcesz wykonać tę operację?',
        confirmText = 'Potwierdź',
        cancelText = 'Anuluj',
        confirmClass = 'btn-danger',
        icon = null,
        onConfirm = () => {}
    } = options;
    const isDestructive = String(confirmClass).split(/\s+/).includes('btn-danger');
    const iconName = String(icon || (isDestructive ? 'trash-2' : 'triangle-alert')).replace(/[^a-z0-9-]/gi, '');
    const previouslyFocused = document.activeElement;
    const modalSequence = (window.__ancoreConfirmModalSequence || 0) + 1;
    const titleId = `confirm-modal-title-${modalSequence}`;
    const messageId = `confirm-modal-message-${modalSequence}`;
    window.__ancoreConfirmModalSequence = modalSequence;

    const overlay = document.createElement('div');
    overlay.className = 'confirm-modal-overlay';
    if (document.querySelector('.tasks-page')) {
        overlay.classList.add('confirm-modal-overlay--tasks');
    }
    if (isDestructive) {
        overlay.classList.add('confirm-modal-overlay--destructive');
    }

    const modal = document.createElement('div');
    modal.className = 'confirm-modal';
    if (overlay.classList.contains('confirm-modal-overlay--tasks')) {
        modal.classList.add('confirm-modal--tasks');
    }
    if (isDestructive) {
        modal.classList.add('confirm-modal--destructive');
    }
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-labelledby', titleId);
    modal.setAttribute('aria-describedby', messageId);
    modal.innerHTML = `
        <div class="confirm-modal__body">
            <div class="confirm-modal__icon">
                <i data-icon="${iconName}" aria-hidden="true"></i>
            </div>
            <div class="confirm-modal__content">
                <h3 class="confirm-modal__title" id="${titleId}">${title}</h3>
                <p class="confirm-modal__message" id="${messageId}">${message}</p>
            </div>
        </div>
        <div class="confirm-modal__footer">
            <button type="button" class="btn-cancel" data-confirm-modal-cancel>${cancelText}</button>
            <button type="button" class="btn ${confirmClass}" data-confirm-modal-confirm>${confirmText}</button>
        </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    window.AncoreIcons?.render(modal);

    const cancelButton = modal.querySelector('[data-confirm-modal-cancel]');
    const confirmButton = modal.querySelector('[data-confirm-modal-confirm]');

    requestAnimationFrame(() => {
        overlay.classList.add('is-visible');
        modal.classList.add('is-visible');
        confirmButton?.focus();
    });

    const closeModal = () => {
        document.removeEventListener('keydown', handleKeyDown);
        overlay.classList.remove('is-visible');
        modal.classList.remove('is-visible');
        setTimeout(() => {
            overlay.remove();
            if (previouslyFocused instanceof HTMLElement && previouslyFocused.isConnected) {
                previouslyFocused.focus({ preventScroll: true });
            }
        }, 150);
    };

    cancelButton?.addEventListener('click', closeModal);

    confirmButton?.addEventListener('click', () => {
        closeModal();
        onConfirm();
    });

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            closeModal();
        } else if (e.key === 'Enter' && document.activeElement === cancelButton) {
            e.preventDefault();
            closeModal();
        } else if (e.key === 'Enter' && document.activeElement === confirmButton) {
            e.preventDefault();
            closeModal();
            onConfirm();
        } else if (e.key === 'Tab' && cancelButton && confirmButton) {
            if (e.shiftKey && document.activeElement === cancelButton) {
                e.preventDefault();
                confirmButton.focus();
            } else if (!e.shiftKey && document.activeElement === confirmButton) {
                e.preventDefault();
                cancelButton.focus();
            }
        }
    };
    document.addEventListener('keydown', handleKeyDown);
};

window.getCookie = function (name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
};
