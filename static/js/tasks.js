document.addEventListener('DOMContentLoaded', function() {
    const taskRows = document.querySelectorAll('.task-row[data-href]');

    // Navigate to task detail on row click
    taskRows.forEach(row => {
        row.addEventListener('click', function(e) {
            if (e.target.type === 'checkbox') return;
            window.location.href = this.dataset.href;
        });
    });
});
