/**
 * Universal Confirmation Modal
 * @param {Object} options - Configuration options
 * @param {string} options.title - Modal title
 * @param {string} options.message - Modal message
 * @param {string} options.confirmText - Text for confirm button
 * @param {string} options.cancelText - Text for cancel button
 * @param {string} options.confirmClass - CSS class for confirm button (e.g., 'btn-danger')
 * @param {Function} options.onConfirm - Callback on confirmation
 */
window.showConfirmModal = function(options) {
    const {
        title = 'Potwierdzenie',
        message = 'Czy na pewno chcesz wykonać tę operację?',
        confirmText = 'Potwierdź',
        cancelText = 'Anuluj',
        confirmClass = 'btn-danger',
        onConfirm = () => {}
    } = options;

    // Create modal overlay
    const overlay = document.createElement('div');
    overlay.className = 'confirm-modal-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(15, 23, 42, 0.5);
        backdrop-filter: blur(4px);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        opacity: 0;
        transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    `;

    // Create modal container
    const container = document.createElement('div');
    container.className = 'confirm-modal-container';
    container.style.cssText = `
        background: var(--card-bg);
        width: 100%;
        max-width: 440px;
        border-radius: 0;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        transform: translateY(10px);
        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        overflow: hidden;
        border: 1px solid var(--border-color);
    `;

    container.innerHTML = `
        <div style="padding: 1.5rem 1.5rem 0 1.5rem; display: flex; align-items: flex-start; gap: 1.25rem;">
            <div style="width: 48px; height: 48px; background: #fee2e2; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--accent-red)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
            </div>
            <div style="flex: 1; text-align: left;">
                <h3 style="margin: 0 0 0.5rem 0; color: var(--sidebar-bg); font-size: 1.125rem; font-weight: 700;">${title}</h3>
                <p style="margin: 0; color: var(--text-muted); line-height: 1.5; font-size: 0.9375rem;">${message}</p>
            </div>
        </div>
        <div style="padding: 1.25rem 1.5rem; display: flex; justify-content: flex-end; gap: 0.75rem; background: var(--bg-main); border-top: 1px solid var(--border-color); margin-top: 1.5rem;">
            <button id="modal-cancel-btn" style="
                border: 1px solid var(--border-color);
                background: var(--card-bg);
                color: var(--text-main);
                font-weight: 600;
                padding: 0.625rem 1.25rem;
                cursor: pointer;
                border-radius: 0;
                font-size: 0.875rem;
                transition: all 0.2s;
            ">${cancelText}</button>
            <button id="modal-confirm-btn" style="
                border: none;
                background: var(--accent-red);
                color: white;
                font-weight: 600;
                padding: 0.625rem 1.25rem;
                cursor: pointer;
                border-radius: 0;
                font-size: 0.875rem;
                transition: all 0.2s;
            ">${confirmText}</button>
        </div>
    `;

    overlay.appendChild(container);
    document.body.appendChild(overlay);

    // Fade in
    requestAnimationFrame(() => {
        overlay.style.opacity = '1';
        container.style.transform = 'translateY(0)';
    });

    const closeModal = () => {
        overlay.style.opacity = '0';
        container.style.transform = 'translateY(10px)';
        setTimeout(() => {
            if (overlay.parentNode) {
                document.body.removeChild(overlay);
            }
        }, 300);
    };

    document.getElementById('modal-cancel-btn').addEventListener('click', closeModal);
    
    document.getElementById('modal-confirm-btn').addEventListener('click', () => {
        closeModal();
        onConfirm();
    });

    // Close on escape
    const handleEsc = (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.removeEventListener('keydown', handleEsc);
        }
    };
    document.addEventListener('keydown', handleEsc);

    // Hover effects
    const cancelBtn = document.getElementById('modal-cancel-btn');
    const confirmBtn = document.getElementById('modal-confirm-btn');
    
    cancelBtn.onmouseover = () => {
        cancelBtn.style.background = 'var(--bg-main)';
        cancelBtn.style.borderColor = 'var(--text-muted)';
    };
    cancelBtn.onmouseout = () => {
        cancelBtn.style.background = 'var(--card-bg)';
        cancelBtn.style.borderColor = 'var(--border-color)';
    };
    
    confirmBtn.onmouseover = () => {
        confirmBtn.style.opacity = '0.9';
    };
    confirmBtn.onmouseout = () => {
        confirmBtn.style.opacity = '1';
    };
};

document.addEventListener('DOMContentLoaded', function() {
    const openModalBtn = document.getElementById('open-task-modal');
    const closeModalBtn = document.getElementById('close-task-modal');
    const cancelModalBtn = document.getElementById('cancel-task-modal');
    const modal = document.getElementById('task-modal');

    if (openModalBtn && modal) {
        openModalBtn.addEventListener('click', function(e) {
            e.preventDefault();
            modal.classList.add('active');
            document.body.classList.add('modal-open');
            // Update URL without reload
            history.pushState({modal: true}, '', '/tasks/create-task/');
        });
    }

    const closeModal = function() {
        if (!modal) return;
        modal.classList.remove('active');
        document.body.classList.remove('modal-open');
        // Revert URL
        if (window.location.pathname === '/tasks/create-task/') {
            history.pushState({modal: false}, '', '/tasks/');
        }
    };

    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeModal);
    }

    if (cancelModalBtn) {
        cancelModalBtn.addEventListener('click', closeModal);
    }

    // Close on click outside
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeModal();
            }
        });
    }

    // Handle back/forward browser buttons
    window.addEventListener('popstate', function(event) {
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
