document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const selectedCountSpan = document.getElementById('selected-count');
    const filterStatus = document.getElementById('filter-status');
    const filterPriority = document.getElementById('filter-priority');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const checkboxes = document.querySelectorAll('.task-checkbox');

    // Navigate to task detail on row click
    taskRows.forEach(row => {
        row.addEventListener('click', function(e) {
            // Prevent navigation if clicking on checkbox or its container cell
            if (e.target.type === 'checkbox' || e.target.closest('td').querySelector('.task-checkbox')) {
                return;
            }
            const viewUrl = this.getAttribute('data-view-url');
            if (viewUrl) window.location.href = viewUrl;
        });
    });

    // Checkbox functionality
    function updateSelection() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        // Exclude select-all checkbox from the count
        const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        const count = selectedTaskCheckboxes.length;

        if (selectedCountSpan) {
            selectedCountSpan.textContent = `${count} wybranych`;
        }

        if (deleteBtn) {
            if (count > 0) {
                deleteBtn.style.visibility = 'visible';
                deleteBtn.style.opacity = '1';
                deleteBtn.disabled = false;
            } else {
                deleteBtn.style.visibility = 'hidden';
                deleteBtn.style.opacity = '0';
                deleteBtn.disabled = true;
            }
        }

        // Highlight rows
        checkboxes.forEach(cb => {
            const row = cb.closest('.task-row');
            if (row) {
                if (cb.checked) {
                    row.classList.add('checked');
                    row.style.backgroundColor = '#eff6ff';
                } else {
                    row.classList.remove('checked');
                    row.style.backgroundColor = '';
                }
            }
        });

        // Update select all state
        if (selectAllCheckbox) {
            const taskCheckboxes = Array.from(checkboxes).filter(cb => cb.id !== 'select-all-checkbox');
            selectAllCheckbox.checked = count === taskCheckboxes.length && taskCheckboxes.length > 0;
        }
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            checkboxes.forEach(cb => cb.checked = this.checked);
            updateSelection();
        });
    }

    checkboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            updateSelection();
        });
    });

    // Initialize state
    updateSelection();

    // Delete selected tasks
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            
            const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
            const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
            const taskIds = selectedTaskCheckboxes.map(cb => {
                const row = cb.closest('.task-row');
                return row ? row.dataset.taskId : null;
            }).filter(id => id !== null);
            
            if (taskIds.length > 0) {
                window.showConfirmModal({
                    title: 'Potwierdź usunięcie',
                    message: `Czy na pewno chcesz usunąć ${taskIds.length} ${taskIds.length === 1 ? 'zadanie' : 'zadań'}? Tej operacji nie można cofnąć.`,
                    confirmText: 'Usuń',
                    cancelText: 'Anuluj',
                    confirmClass: 'btn-danger',
                    onConfirm: () => {
                        fetch('/tasks/delete/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                task_ids: taskIds.map(id => parseInt(id))
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                selectedTaskCheckboxes.forEach(cb => {
                                    cb.closest('.task-row').remove();
                                });
                                updateSelection();
                                showMessage(data.message, 'success');
                            } else {
                                showMessage(data.message || 'Błąd podczas usuwania zadań', 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showMessage('Błąd podczas usuwania zadań', 'error');
                        });
                    }
                });
            }
        });
    }

    // Filtering Logic
    function applyFilters() {
        if (!filterStatus || !filterPriority) return;
        const statusVal = filterStatus.value;
        const priorityVal = filterPriority.value;

        taskRows.forEach(row => {
            const rowStatus = row.getAttribute('data-status');
            const rowPriority = row.getAttribute('data-priority');
            
            const matchesStatus = !statusVal || rowStatus === statusVal;
            const matchesPriority = !priorityVal || rowPriority === priorityVal;

            row.style.display = (matchesStatus && matchesPriority) ? '' : 'none';
        });
    }

    if (filterStatus) filterStatus.addEventListener('change', applyFilters);
    if (filterPriority) filterPriority.addEventListener('change', applyFilters);

    // Helper functions


    function showMessage(message, type) {
        let container = document.querySelector('.notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('hiding');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
});
