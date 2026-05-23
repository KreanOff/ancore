document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const editBtn = document.getElementById('edit-selected-btn');
    const statusToggleBtn = document.getElementById('status-toggle-btn');
    const selectionActions = document.getElementById('selection-actions');
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

        if (selectionActions) {
            if (count > 0) {
                selectionActions.style.visibility = 'visible';
                selectionActions.style.opacity = '1';
                
                // Show Edit only if exactly 1 is selected
                if (editBtn) {
                    editBtn.classList.toggle('u-hidden', count !== 1);
                }

                // Update Status Toggle Button
                if (statusToggleBtn) {
                    const statuses = Array.from(selectedTaskCheckboxes).map(cb => cb.closest('.task-row').dataset.status);
                    const anyOpen = statuses.some(s => s !== 'closed');
                    
                    if (anyOpen) {
                        statusToggleBtn.className = 'btn btn-success tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            Zamknij zadanie
                        `;
                        statusToggleBtn.dataset.targetStatus = 'closed';
                    } else {
                        statusToggleBtn.className = 'btn btn-secondary tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                            Otwórz ponownie
                        `;
                        statusToggleBtn.dataset.targetStatus = 'reopened';
                    }
                }
            } else {
                selectionActions.style.visibility = 'hidden';
                selectionActions.style.opacity = '0';
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

    // Edit selected task
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            const selectedCheckbox = document.querySelector('.task-checkbox:checked');
            if (selectedCheckbox) {
                const taskId = selectedCheckbox.dataset.taskId;
                window.location.href = `/tasks/edit-task/${taskId}/`;
            }
        });
    }

    // Status Toggle selected tasks
    if (statusToggleBtn) {
        statusToggleBtn.addEventListener('click', function() {
            const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
            const taskIds = Array.from(selectedCheckboxes).map(cb => parseInt(cb.dataset.taskId));
            const targetStatus = this.dataset.targetStatus;
            const isClosing = targetStatus === 'closed';
            
            if (taskIds.length > 0) {
                window.showConfirmModal({
                    title: isClosing ? 'Zamknij zadania' : 'Otwórz ponownie zadania',
                    message: `Czy na pewno chcesz ${isClosing ? 'zamknąć' : 'ponownie otworzyć'} ${taskIds.length} ${taskIds.length === 1 ? 'zadanie' : 'zadań'}?`,
                    confirmText: isClosing ? 'Zamknij' : 'Otwórz ponownie',
                    cancelText: 'Anuluj',
                    confirmClass: isClosing ? 'btn-success' : 'btn-secondary',
                    onConfirm: () => {
                        fetch('/tasks/bulk-update-status/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': window.getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                task_ids: taskIds,
                                status: targetStatus
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                window.location.reload();
                            } else {
                                showMessage(data.message || 'Błąd podczas aktualizacji zadań', 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showMessage('Błąd podczas aktualizacji zadań', 'error');
                        });
                    }
                });
            }
        });
    }

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
