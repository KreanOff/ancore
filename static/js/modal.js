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
        if (window.location.pathname === '/tasks/create-task/') {
            modal.classList.add('active');
            document.body.classList.add('modal-open');
        } else {
            modal.classList.remove('active');
            document.body.classList.remove('modal-open');
        }
    });
});
