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
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
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

    requestAnimationFrame(() => {
        overlay.classList.add('is-visible');
        modal.classList.add('is-visible');
        document.getElementById('modal-confirm-btn')?.focus();
    });

    const closeModal = () => {
        document.removeEventListener('keydown', handleKeyDown);
        overlay.classList.remove('is-visible');
        modal.classList.remove('is-visible');
        setTimeout(() => overlay.remove(), 300);
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

document.addEventListener('DOMContentLoaded', function () {
    const openModalBtn = document.getElementById('open-task-modal');
    const closeModalBtn = document.getElementById('close-task-modal');
    const cancelModalBtn = document.getElementById('cancel-task-modal');
    const modal = document.getElementById('task-modal');

    if (openModalBtn && modal) {
        openModalBtn.addEventListener('click', function (e) {
            e.preventDefault();
            modal.classList.add('active');
            document.body.classList.add('modal-open');
            history.pushState({ modal: true }, '', '/tasks/create-task/');
        });
    }

    const closeModal = function () {
        if (!modal) return;
        modal.classList.remove('active');
        document.body.classList.remove('modal-open');
        if (window.location.pathname === '/tasks/create-task/') {
            history.pushState({ modal: false }, '', '/tasks/');
        }
    };

    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if (cancelModalBtn) cancelModalBtn.addEventListener('click', closeModal);

    if (modal) {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) closeModal();
        });
    }

    window.addEventListener('popstate', function () {
        if (!modal) return;
        if (window.location.pathname === '/tasks/create-task/') {
            modal.classList.add('active');
            document.body.classList.add('modal-open');
        } else {
            modal.classList.remove('active');
            document.body.classList.remove('modal-open');
        }
    });
});

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
