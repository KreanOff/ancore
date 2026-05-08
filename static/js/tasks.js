document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row[data-href]');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const selectedCount = document.getElementById('selected-count');
    const filterStatus = document.getElementById('filter-status');
    const filterPriority = document.getElementById('filter-priority');

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
    const checkboxes = document.querySelectorAll('.task-checkbox');
    
    function updateDeleteButton() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        const count = selectedCheckboxes.length;
        
        selectedCount.textContent = `${count} item${count !== 1 ? 's' : ''} selected`;
        
        if (count > 0) {
            deleteBtn.disabled = false;
            deleteBtn.style.opacity = '1';
            deleteBtn.style.cursor = 'pointer';
        } else {
            deleteBtn.disabled = true;
            deleteBtn.style.opacity = '0.5';
            deleteBtn.style.cursor = 'not-allowed';
        }
    }

    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function(e) {
            e.stopPropagation();
            updateDeleteButton();
        });
    });

    // Delete selected tasks
    deleteBtn.addEventListener('click', function() {
        const selectedCheckboxes = document.querySelectorAll('.task-checkbox:checked');
        const taskIds = Array.from(selectedCheckboxes).map(cb => 
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
                    selectedCheckboxes.forEach(cb => {
                        cb.closest('.task-row').remove();
                    });
                    updateDeleteButton();
                    
                    // Show success message
                    showMessage(data.message, 'success');
                } else {
                    showMessage(data.message || 'Error deleting tasks', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showMessage('Error deleting tasks', 'error');
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
            <div style="margin-bottom: 1.5rem;">
                <h3 style="margin: 0 0 1rem 0; color: #333; font-size: 1.25rem;">Confirm Deletion</h3>
                <p style="margin: 0; color: #666; line-height: 1.5;">
                    Are you sure you want to delete ${taskCount} task${taskCount !== 1 ? 's' : ''}? This action cannot be undone.
                </p>
            </div>
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <button id="cancel-delete" style="
                    padding: 0.75rem 1.5rem;
                    border: 1px solid #ddd;
                    background: #f8f9fa;
                    color: #666;
                    cursor: pointer;
                    font-size: 0.875rem;
                    font-weight: 500;
                ">Cancel</button>
                <button id="confirm-delete" style="
                    padding: 0.75rem 1.5rem;
                    border: none;
                    background: #dc3545;
                    color: white;
                    cursor: pointer;
                    font-size: 0.875rem;
                    font-weight: 500;
                ">Delete</button>
            </div>
        `;

        modalOverlay.appendChild(modalContent);
        document.body.appendChild(modalOverlay);

        // Add event listeners
        document.getElementById('cancel-delete').addEventListener('click', () => {
            document.body.removeChild(modalOverlay);
        });

        document.getElementById('confirm-delete').addEventListener('click', () => {
            document.body.removeChild(modalOverlay);
            onConfirm();
        });

        // Close modal on overlay click
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                document.body.removeChild(modalOverlay);
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
