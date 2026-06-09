if (document.querySelector('.tasks-page')) {
    document.body.classList.add('tasks-ui');
}

/**
 * Universal Confirmation Modal
 */
window.showConfirmModal = function (options) {
    const {
        title = 'Potwierdzenie',
        message = 'Czy na pewno chcesz wykonać tę operację?',
        confirmText = 'Potwierdź',
        cancelText = 'Anuluj',
        confirmClass = 'btn-danger',
        onConfirm = () => {}
    } = options;

    const overlay = document.createElement('div');
    overlay.className = 'confirm-modal-overlay';
    if (document.querySelector('.tasks-page')) {
        overlay.classList.add('confirm-modal-overlay--tasks');
    }

    const modal = document.createElement('div');
    modal.className = 'confirm-modal';
    if (overlay.classList.contains('confirm-modal-overlay--tasks')) {
        modal.classList.add('confirm-modal--tasks');
    }
    modal.innerHTML = `
        <div class="confirm-modal__body">
            <div class="confirm-modal__icon">
                <i data-lucide="triangle-alert" aria-hidden="true" stroke-width="2.5"></i>
            </div>
            <div class="confirm-modal__content">
                <h3 class="confirm-modal__title">${title}</h3>
                <p class="confirm-modal__message">${message}</p>
            </div>
        </div>
        <div class="confirm-modal__footer">
            <button type="button" id="modal-cancel-btn" class="btn-cancel">${cancelText}</button>
            <button type="button" id="modal-confirm-btn" class="btn ${confirmClass}">${confirmText}</button>
        </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);
    window.AncoreIcons?.render(modal);

    requestAnimationFrame(() => {
        overlay.classList.add('is-visible');
        modal.classList.add('is-visible');
        document.getElementById('modal-confirm-btn')?.focus();
    });

    const closeModal = () => {
        document.removeEventListener('keydown', handleKeyDown);
        overlay.classList.remove('is-visible');
        modal.classList.remove('is-visible');
        setTimeout(() => overlay.remove(), 150);
    };

    document.getElementById('modal-cancel-btn')?.addEventListener('click', closeModal);

    document.getElementById('modal-confirm-btn')?.addEventListener('click', () => {
        closeModal();
        onConfirm();
    });

    const handleKeyDown = (e) => {
        if (e.key === 'Escape') {
            closeModal();
        } else if (e.key === 'Enter') {
            e.preventDefault();
            closeModal();
            onConfirm();
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
