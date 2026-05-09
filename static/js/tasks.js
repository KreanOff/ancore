document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row[data-href]');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const selectedCount = document.getElementById('selected-count');
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
            window.location.href = this.dataset.href;
        });
    });

    // Checkbox functionality
    function updateDeleteButton() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        // Exclude select-all checkbox from the count
        const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        const count = selectedTaskCheckboxes.length;
        
        selectedCount.textContent = `${count} ${count === 1 ? 'element' : 'elementów'} wybranych`;
        
        // Show/hide select all checkbox based on whether any task is selected
        if (count > 0) {
            selectAllCheckbox.style.display = 'inline-block';
            deleteBtn.disabled = false;
        } else {
            selectAllCheckbox.style.display = 'none';
            deleteBtn.disabled = true;
        }
    }

    // Update select all checkbox state
    function updateSelectAllCheckbox() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        const totalCheckboxes = document.querySelectorAll('.task-checkbox');
        
        // Exclude select-all checkbox from the count
        const taskCheckboxes = Array.from(totalCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        const selectedTaskCheckboxes = Array.from(selectedCheckboxes).filter(cb => cb.id !== 'select-all-checkbox');
        
        selectAllCheckbox.checked = selectedTaskCheckboxes.length === taskCheckboxes.length && taskCheckboxes.length > 0;
        selectAllCheckbox.indeterminate = false;
    }

    // Select all checkbox functionality
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

    // Initialize select all checkbox visibility and red highlights on page load
    updateDeleteButton();
    
    // Add red highlight to already checked tasks
    checkboxes.forEach(checkbox => {
        if (checkbox.checked && checkbox.id !== 'select-all-checkbox') {
            checkbox.closest('.task-row').classList.add('checked');
        }
    });

    // Delete selected tasks
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
            showDeleteConfirmation(taskIds.length, () => {
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
            });
        }
    });

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

    // Helper function to show messages
    function showMessage(message, type) {
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            transition: opacity 0.3s ease;
            ${type === 'success' ? 'background-color: #28a745;' : 'background-color: #dc3545;'}
        `;
        messageDiv.textContent = message;
        
        document.body.appendChild(messageDiv);
        
        // Remove message after 3 seconds
        setTimeout(() => {
            messageDiv.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(messageDiv);
            }, 300);
        }, 3000);
    }

    // Helper function to show centered confirmation modal
    function showDeleteConfirmation(taskCount, onConfirm) {
        // Create modal overlay
        const modalOverlay = document.createElement('div');
        modalOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 2000;
        `;

        // Create modal content
        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: white;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            max-width: 400px;
            width: 90%;
            text-align: center;
        `;

        modalContent.innerHTML = `
            <div style="margin-bottom: 1.5rem; text-align: left;">
                <h3 style="margin: 0 0 1rem 0; color: var(--text-main); font-size: 1.25rem;">Potwierdź usunięcie</h3>
                <p style="margin: 0; color: var(--text-muted); line-height: 1.5;">
                    Czy na pewno chcesz usunąć ${taskCount} ${taskCount === 1 ? 'zadanie' : 'zadań'}? Ta czynności nie może być cofnięta.
                </p>
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button id="cancel-delete" style="
                    padding: 0.75rem 1.5rem;
                    border: 1px solid var(--border-color);
                    background: var(--card-bg);
                    color: var(--text-main);
                    cursor: pointer;
                    font-size: 0.875rem;
                    font-weight: 500;
                ">Anuluj</button>
                <button id="confirm-delete" style="
                    padding: 0.75rem 1.5rem;
                    border: none;
                    background: var(--accent-red);
                    color: #ffffff;
                    cursor: pointer;
                    font-size: 0.875rem;
                    font-weight: 500;
                ">Usuń</button>
            </div>
        `;

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        // Function to close modal safely
        function closeModal() {
            if (modalOverlay && modalOverlay.parentNode) {
                document.body.removeChild(modalOverlay);
            }
        }

        // Add event listeners
        document.getElementById('cancel-delete').addEventListener('click', closeModal);

        document.getElementById('confirm-delete').addEventListener('click', () => {
            closeModal();
            onConfirm();
        });

        // Close modal on overlay click
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeModal();
            }
        });

        // Handle Enter key to confirm, Escape to cancel
        document.addEventListener('keydown', function handleKeyDown(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                closeModal();
                onConfirm();
                document.removeEventListener('keydown', handleKeyDown);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                closeModal();
                document.removeEventListener('keydown', handleKeyDown);
            }
        });
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

    filterStatus.addEventListener('change', applyFilters);
    filterPriority.addEventListener('change', applyFilters);
});
