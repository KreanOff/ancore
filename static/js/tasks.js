document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row[data-href]');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const selectedCount = document.getElementById('selected-count');
    const filterStatus = document.getElementById('filter-status');
    const filterPriority = document.getElementById('filter-priority');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const checkboxes = document.querySelectorAll('.task-checkbox');

    // Navigate to task detail on row click
    if (taskRows.length > 0) {
        taskRows.forEach(row => {
            row.addEventListener('click', function(e) {
                // Prevent navigation if clicking on checkbox or its container cell
                if (e.target.type === 'checkbox' || e.target.closest('td').querySelector('.task-checkbox')) {
                    return;
                }
                window.location.href = this.dataset.href;
            });
        });
    }

    // Checkbox functionality
    function updateDeleteButton() {
        if (!selectedCount) return;

        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        // Exclude select-all checkbox from the count
        const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        const count = selectedTaskCheckboxes.length;

        selectedCount.textContent = `${count} ${count === 1 ? 'element' : 'elementów'} wybranych`;

        // Show/hide select all checkbox based on whether any task is selected
        if (count > 0) {
            if (selectAllCheckbox) selectAllCheckbox.style.display = 'inline-block';
            if (deleteBtn) deleteBtn.disabled = false;
        } else {
            if (selectAllCheckbox) selectAllCheckbox.style.display = 'none';
            if (deleteBtn) deleteBtn.disabled = true;
        }
    }

    // Update select all checkbox state
    function updateSelectAllCheckbox() {
        if (!selectAllCheckbox) return;

        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        const totalCheckboxes = document.querySelectorAll('.task-checkbox');

        // Exclude select-all checkbox from the count
        const taskCheckboxes = Array.from(totalCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');

        selectAllCheckbox.checked = selectedTaskCheckboxes.length === taskCheckboxes.length && taskCheckboxes.length > 0;
        selectAllCheckbox.indeterminate = false;
    }

    // Select all checkbox functionality
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            // Only affect task checkboxes, not the select-all checkbox itself
            const taskCheckboxes = Array.from(checkboxes).filter(cb => cb.id !== 'select-all-checkbox');

            taskCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;

                // Toggle red highlight on the row
                const taskRow = checkbox.closest('.task-row');
                if (this.checked) {
                    taskRow.classList.add('checked');
                } else {
                    taskRow.classList.remove('checked');
                }
            });
            updateDeleteButton();
            updateSelectAllCheckbox();
        });
    }

    if (checkboxes.length > 0) {
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function(e) {
                e.stopPropagation();

                // Toggle red highlight on the row
                const taskRow = this.closest('.task-row');
                if (this.checked) {
                    taskRow.classList.add('checked');
                } else {
                    taskRow.classList.remove('checked');
                }

                updateDeleteButton();
                updateSelectAllCheckbox();
            });
        });
    }

    // Initialize select all checkbox visibility and red highlights on page load
    updateDeleteButton();
    
    // Add red highlight to already checked tasks
    checkboxes.forEach(checkbox => {
        if (checkbox.checked && checkbox.id !== 'select-all-checkbox') {
            checkbox.closest('.task-row').classList.add('checked');
        }
    });

    // Delete selected tasks
    if (deleteBtn) {
        deleteBtn.addEventListener('click', function() {
            if (this.disabled) {
                return;
            }
            
            const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
            // Exclude select-all checkbox from task deletion
            const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
            const taskIds = selectedTaskCheckboxes.map(cb => 
                cb.closest('.task-row').dataset.taskId
            );
            
            if (taskIds.length > 0) {
                window.showConfirmModal({
                    title: 'Potwierdź usunięcie',
                    message: `Czy na pewno chcesz usunąć ${taskIds.length} ${taskIds.length === 1 ? 'zadanie' : 'zadań'}? Tej operacji nie można cofnąć.`,
                    confirmText: 'Usuń',
                    cancelText: 'Anuluj',
                    confirmClass: 'btn-danger',
                    onConfirm: () => {
                        // Make AJAX call to delete tasks from database
                        fetch('/tasks/delete/', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCookie('csrftoken')
                            },
                            body: JSON.stringify({
                                task_ids: taskIds.map(id => parseInt(id))
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                // Remove rows from DOM
                                selectedTaskCheckboxes.forEach(cb => {
                                    cb.closest('.task-row').remove();
                                });
                                updateDeleteButton();
                                
                                // Show success message
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

    // Helper function to get CSRF token
    function getCookie(name) {
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
    }

    // Helper function to show messages using global notification system
    function showMessage(message, type) {
        // Create or get notifications container
        let container = document.querySelector('.notifications-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notifications-container';
            document.body.appendChild(container);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        container.appendChild(notification);
        
        // Auto-hide notification after 5 seconds
        setTimeout(() => {
            hideNotification(notification);
        }, 5000);
    }
    
    // Helper function to hide notification (from notifications.js)
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

    // Filter functionality
    function applyFilters() {
        const statusFilter = filterStatus.value;
        const priorityFilter = filterPriority.value;
        
        taskRows.forEach(row => {
            const statusElement = row.querySelector('.status-indicator');
            const priorityElement = row.querySelector('.badge');
            
            let showRow = true;
            
            if (statusFilter && !statusElement.classList.contains(`status-${statusFilter}`)) {
                showRow = false;
            }
            
            if (priorityFilter && !priorityElement.classList.contains(`badge-${priorityFilter}`)) {
                showRow = false;
            }
            
            row.style.display = showRow ? '' : 'none';
        });
    }

    if (filterStatus) {
        filterStatus.addEventListener('change', applyFilters);
    }
    if (filterPriority) {
        filterPriority.addEventListener('change', applyFilters);
    }
});
