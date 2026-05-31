function initTasksPage() {
    const taskRows = document.querySelectorAll('.task-row');
    const projectRows = document.querySelectorAll('.tasks-project-row');
    const sectionRows = document.querySelectorAll('.tasks-section-row');
    const deleteBtn = document.getElementById('delete-selected-btn');
    const editSelectedTaskMenuBtn = document.getElementById('edit-selected-task-menu-btn');
    const editSelectedSectionMenuBtn = document.getElementById('edit-selected-section-menu-btn');
    const editSelectedProjectMenuBtn = document.getElementById('edit-selected-project-menu-btn');
    const editSelectedTagMenuBtn = document.getElementById('edit-selected-tag-menu-btn');
    const deleteSelectedTaskMenuBtn = document.getElementById('delete-selected-task-menu-btn');
    const deleteSelectedSectionMenuBtn = document.getElementById('delete-selected-section-menu-btn');
    const deleteSelectedProjectMenuBtn = document.getElementById('delete-selected-project-menu-btn');
    const deleteSelectedTagMenuBtn = document.getElementById('delete-selected-tag-menu-btn');
    const editBtn = document.getElementById('edit-selected-btn');
    const statusToggleBtn = document.getElementById('status-toggle-btn');
    const selectionActions = document.getElementById('selection-actions');
    const selectedCountSpan = document.getElementById('selected-count');
    const filterStatus = document.getElementById('filter-status');
    const filterPriority = document.getElementById('filter-priority');
    const filterSearch = document.getElementById('filter-search');
    const filterButtons = document.querySelectorAll('[data-status-filter], [data-priority-filter]');
    const statusFilterMenu = document.querySelector('[data-status-filter-menu]');
    const statusFilterToggle = document.querySelector('[data-status-filter-toggle]');
    const statusFilterLabel = document.querySelector('[data-status-filter-label]');
    const statusFilterIcon = document.querySelector('[data-status-filter-icon]');
    const priorityFilterMenu = document.querySelector('[data-priority-filter-menu]');
    const priorityFilterToggle = document.querySelector('[data-priority-filter-toggle]');
    const priorityFilterLabel = document.querySelector('[data-priority-filter-label]');
    const priorityFilterIcon = document.querySelector('[data-priority-filter-icon]');
    const groupRows = document.querySelectorAll('.tasks-group-row');
    const issueGroups = document.querySelectorAll('.tasks-issue-group');
    const statusSubgroups = document.querySelectorAll('.tasks-status-subgroup');
    const collapsibleGroupHeaders = document.querySelectorAll('.tasks-issue-group-header, .tasks-status-subgroup-header');
    const subtasksToolbar = document.querySelector('.tasks-subtasks-toolbar');
    const subtasksBoard = document.querySelector('.tasks-subtasks-board');
    const subtasksCollapseButton = document.querySelector('[data-subtasks-collapse]');
    const subtasksSortButton = document.querySelector('[data-subtasks-sort]');
    const subtasksDeleteButton = document.querySelector('[data-subtasks-delete]');
    const descriptionInput = document.querySelector('.tasks-issue-description-field textarea[name="description"]');
    const descriptionEditor = enhanceDescriptionEditor(descriptionInput);
    const issueDetailMain = document.querySelector('.tasks-issue-main');
    const issueSidebarResizer = document.querySelector('[data-issue-sidebar-resizer]');
    const selectAllCheckbox = document.getElementById('select-all-checkbox');
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const sectionCheckboxes = document.querySelectorAll('.tasks-section-row .tasks-row-checkbox[data-section-id]');
    const projectCheckboxes = document.querySelectorAll('.tasks-project-row .tasks-row-checkbox[data-project-id]');
    const tagCheckboxes = document.querySelectorAll('.tasks-all-groups-row .tasks-row-checkbox[data-tag-id]');
    const sectionCopyRoot = document.querySelector('[data-section-empty-label], [data-section-delete-title]');
    const sectionCopy = {
        emptyLabel: sectionCopyRoot?.dataset.sectionEmptyLabel || 'Wybierz grupę',
        deleteFallback: sectionCopyRoot?.dataset.sectionDeleteFallback || 'tę grupę',
        deleteTitle: sectionCopyRoot?.dataset.sectionDeleteTitle || 'Usuń grupę',
        deleteConfirm: sectionCopyRoot?.dataset.sectionDeleteConfirm || 'Usuń grupę',
        deleteMessageTemplate: sectionCopyRoot?.dataset.sectionDeleteMessageTemplate || 'Czy na pewno chcesz usunąć grupę „{title}”? Zadania z grupy zostaną przeniesione do sekcji „Bez przestrzeni roboczej”.'
    };
    const createMenu = document.querySelector('[data-create-menu]');
    const createMenuToggle = document.getElementById('open-create-menu');
    const createMenuPanel = document.getElementById('create-menu-panel');
    const sectionActionMenu = document.querySelector('[data-section-actions]');
    const projectActionMenus = document.querySelectorAll('[data-project-actions]');
    const projectTree = document.querySelector('[data-project-tree]');
    const projectTreeToggle = document.querySelector('[data-project-tree-toggle]');
    const projectNodes = document.querySelectorAll('[data-project-node]');
    const openProjectButtons = document.querySelectorAll('[data-open-project]');
    const openTagButtons = document.querySelectorAll('[data-open-tag]');
    const openProjectRenameButtons = document.querySelectorAll('[data-open-project-rename]');
    const openSectionCreateButtons = document.querySelectorAll('[data-open-section-create]');
    const openIssueButtons = document.querySelectorAll('#open-issue-modal, [data-open-issue]');
    const projectModal = document.getElementById('project-modal');
    const tagModal = document.getElementById('tag-modal');
    const projectRenameModal = document.getElementById('project-rename-modal');
    const sectionCreateModal = document.getElementById('section-create-modal');
    const sectionRenameModal = document.getElementById('section-rename-modal');
    const issueModal = document.getElementById('issue-modal');
    const projectForm = document.getElementById('project-create-form');
    const tagForm = document.getElementById('tag-create-form');
    const projectRenameForm = document.getElementById('project-rename-form');
    const sectionCreateForm = document.getElementById('section-create-form');
    const sectionRenameForm = document.getElementById('section-rename-form');
    const issueForm = document.getElementById('issue-create-form');
    const projectNameInput = projectForm ? projectForm.querySelector('[name="name"]') : null;
    const tagActionInput = tagForm ? tagForm.querySelector('[name="action"]') : null;
    const tagIdInput = tagForm ? tagForm.querySelector('[name="tag_id"]') : null;
    const tagNameInput = tagForm ? tagForm.querySelector('[name="name"]') : null;
    const tagDescriptionInput = tagForm ? tagForm.querySelector('[name="description"]') : null;
    const projectRenameNameInput = projectRenameForm ? projectRenameForm.querySelector('[name="name"]') : null;
    const projectRenameDescriptionInput = projectRenameForm ? projectRenameForm.querySelector('[name="description"]') : null;
    const projectRenameCodeValue = document.getElementById('project-rename-code');

    const taskAppSegment = window.location.pathname.split('/').filter(Boolean)[0] === 'kanban' ? 'kanban' : 'tasks';
    const taskCopy = taskAppSegment === 'kanban'
        ? {
            itemAcc: 'kartę',
            itemPluralGen: 'kart',
            itemMoveError: 'Błąd podczas przenoszenia karty',
            itemDeleteError: 'Błąd podczas usuwania kart',
            itemUpdateError: 'Błąd podczas aktualizacji kart',
            closeOne: 'Zamknij kartę',
            closeMany: 'Zamknij karty',
            reopenMany: 'Otwórz ponownie karty',
            subItems: 'Podkarty',
            subItemAcc: 'podkartę',
            projectDeleteNote: 'Karty z tej przestrzeni zostaną przeniesione do sekcji „Bez przestrzeni roboczej”.',
            tagDetachNote: 'Tag zostanie odpięty od kart.'
        }
        : {
            itemAcc: 'zadanie',
            itemPluralGen: 'zadań',
            itemMoveError: 'Błąd podczas przenoszenia zadania',
            itemDeleteError: 'Błąd podczas usuwania zadań',
            itemUpdateError: 'Błąd podczas aktualizacji zadań',
            closeOne: 'Zamknij zadanie',
            closeMany: 'Zamknij zadania',
            reopenMany: 'Otwórz ponownie zadania',
            subItems: 'Podzadania',
            subItemAcc: 'podzadanie',
            projectDeleteNote: 'Zadania z tej przestrzeni zostaną przeniesione do sekcji „Bez przestrzeni roboczej”.',
            tagDetachNote: 'Tag zostanie odpięty od zadań.'
        };
    const taskReturnStorageKey = `${taskAppSegment}:lastTaskReturn`;
    const taskReturnRestoreKey = `${taskAppSegment}:restoreTaskReturn`;

    initKanbanColumnCreateForms();
    initKanbanColumnReorder();
    initKanbanWallpapers();

    function initKanbanWallpapers() {
        const panel = document.querySelector('[data-kanban-wallpaper-panel]');
        const toggle = document.querySelector('[data-kanban-wallpaper-toggle]');
        const closeButton = document.querySelector('[data-kanban-wallpaper-close]');
        const input = document.querySelector('[data-kanban-wallpaper-input]');
        const list = document.querySelector('[data-kanban-wallpaper-list]');
        const clearButton = document.querySelector('[data-kanban-wallpaper-clear]');
        const boards = document.querySelectorAll('.tasks-kanban-board');

        if (!boards.length) return;

        const wallpapersKey = 'ancore:kanban:wallpapers';
        const selectedKey = `ancore:kanban:wallpaper:${window.location.pathname}`;

        function readWallpapers() {
            try {
                const value = JSON.parse(localStorage.getItem(wallpapersKey) || '[]');
                return Array.isArray(value) ? value : [];
            } catch (error) {
                return [];
            }
        }

        function writeWallpapers(wallpapers) {
            try {
                localStorage.setItem(wallpapersKey, JSON.stringify(wallpapers));
                return true;
            } catch (error) {
                showTaskNotification('Nie udało się zapisać tapety lokalnie', 'error');
                return false;
            }
        }

        function getSelectedWallpaperId() {
            try {
                return localStorage.getItem(selectedKey) || '';
            } catch (error) {
                return '';
            }
        }

        function setSelectedWallpaperId(id) {
            try {
                if (id) {
                    localStorage.setItem(selectedKey, id);
                } else {
                    localStorage.removeItem(selectedKey);
                }
            } catch (error) {
                showTaskNotification('Nie udało się zapisać wyboru tapety', 'error');
            }
        }

        function applyWallpaper() {
            const selectedId = getSelectedWallpaperId();
            const selected = readWallpapers().find(wallpaper => wallpaper.id === selectedId);

            boards.forEach(board => {
                if (selected?.dataUrl) {
                    board.style.backgroundImage = `url("${selected.dataUrl}")`;
                    board.classList.add('has-wallpaper');
                } else {
                    board.style.backgroundImage = '';
                    board.classList.remove('has-wallpaper');
                }
            });
        }

        function renderWallpapers() {
            if (!list) return;

            const wallpapers = readWallpapers();
            const selectedId = getSelectedWallpaperId();
            list.innerHTML = '';

            wallpapers.forEach(wallpaper => {
                const swatch = document.createElement('div');
                swatch.className = `tasks-kanban-wallpaper-swatch${wallpaper.id === selectedId ? ' is-active' : ''}`;

                const preview = document.createElement('button');
                preview.type = 'button';
                preview.className = 'tasks-kanban-wallpaper-swatch__preview';
                preview.style.backgroundImage = `url("${wallpaper.dataUrl}")`;
                preview.setAttribute('aria-label', `Ustaw tapetę ${wallpaper.name || ''}`.trim());
                preview.title = wallpaper.name || 'Tapeta';
                preview.addEventListener('click', () => {
                    setSelectedWallpaperId(wallpaper.id);
                    applyWallpaper();
                    renderWallpapers();
                });

                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'tasks-kanban-wallpaper-swatch__remove';
                remove.textContent = '×';
                remove.setAttribute('aria-label', 'Usuń tapetę');
                remove.addEventListener('click', event => {
                    event.stopPropagation();
                    const nextWallpapers = readWallpapers().filter(item => item.id !== wallpaper.id);
                    if (!writeWallpapers(nextWallpapers)) return;
                    if (getSelectedWallpaperId() === wallpaper.id) {
                        setSelectedWallpaperId('');
                        applyWallpaper();
                    }
                    renderWallpapers();
                });

                swatch.appendChild(preview);
                swatch.appendChild(remove);
                list.appendChild(swatch);
            });
        }

        function resizeWallpaper(file) {
            return new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onerror = () => reject(new Error('Nie udało się odczytać pliku'));
                reader.onload = () => {
                    const image = new Image();
                    image.onerror = () => reject(new Error('Nie udało się wczytać obrazu'));
                    image.onload = () => {
                        const maxSize = 1920;
                        const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
                        const width = Math.max(1, Math.round(image.width * scale));
                        const height = Math.max(1, Math.round(image.height * scale));
                        const canvas = document.createElement('canvas');
                        canvas.width = width;
                        canvas.height = height;
                        const context = canvas.getContext('2d');
                        if (!context) {
                            reject(new Error('Nie udało się przygotować tapety'));
                            return;
                        }
                        context.drawImage(image, 0, 0, width, height);
                        resolve(canvas.toDataURL('image/jpeg', 0.86));
                    };
                    image.src = reader.result;
                };
                reader.readAsDataURL(file);
            });
        }

        applyWallpaper();

        if (!panel || !toggle || toggle.dataset.wallpaperInitialized === 'true') return;
        toggle.dataset.wallpaperInitialized = 'true';
        renderWallpapers();

        toggle.addEventListener('click', () => {
            const willOpen = panel.hidden;
            closeSectionActionMenu();
            panel.hidden = !willOpen;
            toggle.setAttribute('aria-expanded', String(willOpen));
            if (willOpen) renderWallpapers();
        });

        closeButton?.addEventListener('click', () => {
            panel.hidden = true;
            toggle.setAttribute('aria-expanded', 'false');
        });

        clearButton?.addEventListener('click', () => {
            setSelectedWallpaperId('');
            applyWallpaper();
            renderWallpapers();
        });

        input?.addEventListener('change', async () => {
            const file = input.files?.[0];
            if (!file) return;

            try {
                const dataUrl = await resizeWallpaper(file);
                const wallpaper = {
                    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
                    name: file.name,
                    dataUrl,
                };
                const nextWallpapers = [wallpaper, ...readWallpapers()].slice(0, 12);
                if (!writeWallpapers(nextWallpapers)) return;
                setSelectedWallpaperId(wallpaper.id);
                applyWallpaper();
                renderWallpapers();
            } catch (error) {
                showTaskNotification(error.message || 'Nie udało się dodać tapety', 'error');
            } finally {
                input.value = '';
            }
        });
    }

    function initKanbanColumnCreateForms() {
        function closeColumnCreateForm(column) {
            const button = column.querySelector('[data-kanban-column-create-toggle]');
            const form = column.querySelector('.tasks-kanban-column__create-form');

            if (!button || !form || form.hidden) return;

            form.hidden = true;
            button.hidden = false;
            column.classList.remove('is-creating');
        }

        document.querySelectorAll('[data-kanban-column-create-toggle]').forEach(button => {
            if (button.dataset.initialized === 'true') return;
            button.dataset.initialized = 'true';

            button.addEventListener('click', () => {
                const column = button.closest('.tasks-kanban-column--new');
                const form = column ? column.querySelector('.tasks-kanban-column__create-form') : null;
                const input = form ? form.querySelector('input[name="title"]') : null;

                if (!form) return;

                document.querySelectorAll('.tasks-kanban-column--new.is-creating').forEach(openColumn => {
                    if (openColumn !== column) closeColumnCreateForm(openColumn);
                });
                button.hidden = true;
                form.hidden = false;
                column?.classList.add('is-creating');
                input?.focus();
            });
        });

        if (window.ancoreKanbanColumnCreateOutsideInitialized) return;
        window.ancoreKanbanColumnCreateOutsideInitialized = true;

        document.addEventListener('click', event => {
            document.querySelectorAll('.tasks-kanban-column--new.is-creating').forEach(column => {
                if (!column.contains(event.target)) closeColumnCreateForm(column);
            });
        });
    }

    function initKanbanColumnReorder() {
        document.querySelectorAll('[data-kanban-column-reorder-url]').forEach(board => {
            if (board.dataset.columnReorderInitialized === 'true') return;
            board.dataset.columnReorderInitialized = 'true';

            let draggedColumn = null;
            let originalOrder = [];

            function orderedColumnIds() {
                return Array.from(board.querySelectorAll(':scope > .tasks-kanban-column[data-kanban-column-id]'))
                    .map(column => column.dataset.kanbanColumnId);
            }

            function reorderableColumns() {
                return Array.from(board.querySelectorAll(':scope > .tasks-kanban-column[data-kanban-column-id]'));
            }

            function newColumnPanel() {
                return board.querySelector(':scope > .tasks-kanban-column--new');
            }

            function insertBeforeNewColumn(column) {
                board.insertBefore(column, newColumnPanel() || null);
            }

            function captureColumnPositions() {
                return new Map(
                    reorderableColumns().map(column => [column, column.getBoundingClientRect().left])
                );
            }

            function animateColumnShift(previousPositions) {
                reorderableColumns().forEach(column => {
                    if (column === draggedColumn) return;

                    const previousLeft = previousPositions.get(column);
                    if (previousLeft === undefined) return;

                    const nextLeft = column.getBoundingClientRect().left;
                    const offset = previousLeft - nextLeft;
                    if (!offset) return;

                    column.style.transition = 'none';
                    column.style.transform = `translateX(${offset}px)`;
                    column.getBoundingClientRect();

                    requestAnimationFrame(() => {
                        column.style.transition = 'transform 180ms cubic-bezier(0.2, 0.8, 0.2, 1)';
                        column.style.transform = '';
                    });

                    column.addEventListener('transitionend', () => {
                        column.style.transition = '';
                        column.style.transform = '';
                    }, { once: true });
                });
            }

            function moveDraggedColumn(beforeColumn) {
                const currentNextColumn = draggedColumn.nextElementSibling;
                const newColumn = newColumnPanel();
                const targetBeforeColumn = beforeColumn || newColumn || null;

                if (currentNextColumn === targetBeforeColumn) return;

                const previousPositions = captureColumnPositions();
                board.insertBefore(draggedColumn, targetBeforeColumn);
                animateColumnShift(previousPositions);
            }

            function restoreOriginalOrder(orderToRestore) {
                const columnsById = new Map(
                    reorderableColumns()
                        .map(column => [column.dataset.kanbanColumnId, column])
                );

                orderToRestore.forEach(columnId => {
                    const column = columnsById.get(columnId);
                    if (column) insertBeforeNewColumn(column);
                });
            }

            function getColumnAfterPointer(pointerX) {
                const columns = reorderableColumns().filter(column => column !== draggedColumn);

                return columns.reduce((closest, column) => {
                    const box = column.getBoundingClientRect();
                    const offset = pointerX - box.left - box.width / 2;
                    if (offset < 0 && offset > closest.offset) {
                        return { offset, column };
                    }
                    return closest;
                }, { offset: Number.NEGATIVE_INFINITY, column: null }).column;
            }

            function persistColumnOrder() {
                const nextOrder = orderedColumnIds();
                if (nextOrder.join(',') === originalOrder.join(',')) return;
                const orderBeforeDrag = [...originalOrder];

                fetch(board.dataset.kanbanColumnReorderUrl, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': window.getCookie('csrftoken')
                    },
                    body: JSON.stringify({ column_ids: nextOrder })
                })
                .then(response => response.json().then(data => ({ ok: response.ok, data })))
                .then(({ ok, data }) => {
                    if (!ok || data.status !== 'success') {
                        throw new Error(data.message || 'Nie udało się zapisać kolejności kolumn');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    restoreOriginalOrder(orderBeforeDrag);
                    showMessage(error.message || 'Nie udało się zapisać kolejności kolumn', 'error');
                });
            }

            board.querySelectorAll(':scope > .tasks-kanban-column[data-kanban-column-id]').forEach(column => {
                column.addEventListener('dragstart', event => {
                    const isCardDrag = event.target.closest('.task-row[draggable="true"], .tasks-issue-row[draggable="true"]');
                    const isInteractiveDrag = event.target.closest('a, button, input, select, textarea, form');
                    if (isCardDrag) return;
                    if (isInteractiveDrag) {
                        event.preventDefault();
                        return;
                    }

                    draggedColumn = column;

                    originalOrder = orderedColumnIds();
                    draggedColumn.classList.add('is-column-dragging');
                    board.classList.add('is-reordering-columns');
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('application/x-kanban-column-id', draggedColumn.dataset.kanbanColumnId);
                });

                column.addEventListener('dragend', event => {
                    if (event.target.closest('.task-row[draggable="true"], .tasks-issue-row[draggable="true"]')) return;
                    if (!draggedColumn) return;

                    draggedColumn.classList.remove('is-column-dragging');
                    board.classList.remove('is-reordering-columns');
                    persistColumnOrder();
                    draggedColumn = null;
                    originalOrder = [];
                });
            });

            board.addEventListener('dragover', event => {
                if (!draggedColumn || !Array.from(event.dataTransfer.types).includes('application/x-kanban-column-id')) return;

                event.preventDefault();
                event.dataTransfer.dropEffect = 'move';
                const afterColumn = getColumnAfterPointer(event.clientX);
                moveDraggedColumn(afterColumn);
            });
        });
    }

    function getTaskScrollSnapshot() {
        const mainContent = document.querySelector('.main-content');
        const tableWrap = document.querySelector('.tasks-list-page .tasks-table-wrap');

        return {
            windowX: window.scrollX,
            windowY: window.scrollY,
            mainX: mainContent ? mainContent.scrollLeft : 0,
            mainY: mainContent ? mainContent.scrollTop : 0,
            tableX: tableWrap ? tableWrap.scrollLeft : 0,
            tableY: tableWrap ? tableWrap.scrollTop : 0,
        };
    }

    function rememberTaskReturnPoint(viewUrl) {
        if (!viewUrl || !viewUrl.includes(`/${taskAppSegment}/view-task/`)) return;

        sessionStorage.setItem(taskReturnStorageKey, JSON.stringify({
            viewUrl,
            returnUrl: window.location.pathname + window.location.search + window.location.hash,
            scroll: getTaskScrollSnapshot(),
            savedAt: Date.now(),
        }));
    }

    function restoreTaskReturnPoint() {
        const restorePayload = sessionStorage.getItem(taskReturnRestoreKey);
        if (!restorePayload) return;

        let returnPoint = null;
        try {
            returnPoint = JSON.parse(restorePayload);
        } catch (error) {
            sessionStorage.removeItem(taskReturnRestoreKey);
            return;
        }

        const currentUrl = window.location.pathname + window.location.search + window.location.hash;
        if (!returnPoint || returnPoint.returnUrl !== currentUrl) return;

        sessionStorage.removeItem(taskReturnRestoreKey);

        const scroll = returnPoint.scroll || {};
        const applyScroll = () => {
            const mainContent = document.querySelector('.main-content');
            const tableWrap = document.querySelector('.tasks-list-page .tasks-table-wrap');

            window.scrollTo(scroll.windowX || 0, scroll.windowY || 0);
            if (mainContent) {
                mainContent.scrollLeft = scroll.mainX || 0;
                mainContent.scrollTop = scroll.mainY || 0;
            }
            if (tableWrap) {
                tableWrap.scrollLeft = scroll.tableX || 0;
                tableWrap.scrollTop = scroll.tableY || 0;
            }
        };

        requestAnimationFrame(() => {
            applyScroll();
            requestAnimationFrame(applyScroll);
        });
    }

    function focusKanbanColumnFromUrl() {
        const params = new URLSearchParams(window.location.search);
        const focusColumnId = params.get('focus_column');
        if (!focusColumnId) return;

        const board = document.querySelector('.tasks-kanban-board');
        const column = Array.from(document.querySelectorAll('.tasks-kanban-column[data-drop-column-id]'))
            .find(element => element.dataset.dropColumnId === focusColumnId);

        if (!board || !column) return;

        const scrollToColumn = () => {
            const boardRect = board.getBoundingClientRect();
            const columnRect = column.getBoundingClientRect();
            const targetLeft = board.scrollLeft + columnRect.left - boardRect.left - 16;

            board.scrollTo({
                left: Math.max(0, targetLeft),
                behavior: 'smooth',
            });
        };

        column.classList.add('is-newly-created');
        requestAnimationFrame(() => {
            scrollToColumn();
            setTimeout(scrollToColumn, 120);
        });

        setTimeout(() => column.classList.remove('is-newly-created'), 1800);
        params.delete('focus_column');
        const nextSearch = params.toString();
        const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ''}${window.location.hash}`;
        window.history.replaceState({}, '', nextUrl);
    }

    restoreTaskReturnPoint();
    focusKanbanColumnFromUrl();
    const projectRenameIconInput = projectRenameForm ? projectRenameForm.querySelector('[name="icon"]') : null;
    const projectRenameIdInput = projectRenameForm ? projectRenameForm.querySelector('[name="project_id"]') : null;
    const sectionCreateTitleInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="title"]') : null;
    const sectionCreateDescriptionInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="description"]') : null;
    const sectionCreateProjectInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="project_id"]') : null;
    const sectionCreateIconInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="icon"]') : null;
    const sectionRenameTitleInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="title"]') : null;
    const sectionRenameDescriptionInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="description"]') : null;
    const sectionRenameIconInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="icon"]') : null;
    const sectionRenameIdInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="section_id"]') : null;
    const issueTitleInput = issueForm ? issueForm.querySelector('[name="title"]') : null;
    const issueProjectInput = issueForm ? issueForm.querySelector('[name="project_id"]') : null;
    const issueColumnInput = issueForm ? issueForm.querySelector('[name="column_id"]') : null;
    const issueSectionSelect = issueForm ? issueForm.querySelector('[name="section"]') : null;
    const issueStatusSelect = issueForm ? issueForm.querySelector('[name="status"]') : null;
    const issueProjectPicker = issueForm ? issueForm.querySelector('[data-issue-project-picker]') : null;
    const issueSectionPicker = issueForm ? issueForm.querySelector('[data-issue-section-picker]') : null;
    const issueProjectOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-project-option]')) : [];
    const issueSectionOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-section-option]')) : [];
    const issuePickerSearchInputs = issueForm ? Array.from(issueForm.querySelectorAll('[data-picker-search]')) : [];
    const projectSubmitBtn = document.getElementById('project-create-submit');
    const tagSubmitBtn = document.getElementById('tag-create-submit');
    const projectRenameSubmitBtn = document.getElementById('project-rename-submit');
    const sectionCreateSubmitBtn = document.getElementById('section-create-submit');
    const sectionRenameSubmitBtn = document.getElementById('section-rename-submit');
    const issueSubmitBtn = document.getElementById('issue-create-submit');
    const projectIconInput = projectForm ? projectForm.querySelector('[name="icon"]') : null;
    const projectIconPickers = document.querySelectorAll('[data-project-icon-picker]');
    const projectIconGroups = [
        { input: projectIconInput, picker: document.getElementById('project-icon-picker') },
        { input: projectRenameIconInput, picker: document.getElementById('project-rename-icon-picker') },
        { input: sectionCreateIconInput, picker: document.getElementById('section-create-icon-picker') },
        { input: sectionRenameIconInput, picker: document.getElementById('section-rename-icon-picker') }
    ];
    const statusLabels = {
        new: 'Nowe',
        in_progress: 'Realizowane',
        resolved: 'Rozwiązane',
        closed: 'Zamknięte',
        reopened: 'Ponownie otwarte'
    };
    document.querySelectorAll('[data-status-filter]').forEach(button => {
        const status = button.dataset.statusFilter;
        const label = getFilterButtonText(button);
        if (status && label) statusLabels[status] = label;
    });
    const projectIconSets = [
        {
            label: 'Najczęstsze',
            icon: '⭐',
            items: ['🚀', '⭐', '✅', '⚙️', '💡', '📌', '📋', '📁', '🔧', '🧩', '🎯', '📈', '🔒', '🛠️', '🧪', '🖥️', '📱', '🌐', '☁️', '✨', '🏆', '🎉', '📍', '🔑', '🧰', '🧱', '🪄', '💎', '🧲', '🗓️', '📎', '🔔', '💬', '📣', '🧠', '🧭', '🏁', '🛡️', '🧿', '📌', '📍', '📎', '📔', '📙', '📚', '🗂️', '🗃️', '🧾', '📊', '📉', '📆', '⏰', '⏳', '🔍', '🔎', '🔗', '🔖', '🏷️', '📦', '📫', '📨', '📥', '📤', '📝', '✏️', '🖊️', '🖋️', '🔐', '🔓']
        },
        {
            label: 'Praca',
            icon: '💼',
            items: ['💼', '📊', '📎', '📝', '📅', '⏱️', '🏷️', '📦', '🗂️', '🧾', '✉️', '🔍', '✅', '❗', '📣', '🤝', '👥', '🧠', '🧭', '📔', '📕', '📗', '📘', '📙', '📚', '📓', '📒', '🗃️', '🗄️', '🗒️', '🧑‍💼', '📇', '🗳️', '📤', '📥', '🪪', '🧳', '🏢', '🏦', '📞', '☎️', '📠', '📧', '📨', '📬', '📭', '📮', '🗞️', '📰', '💬', '💭', '🕘', '🕙', '🗓️', '📈', '📉', '💹', '🧮', '💳', '💵', '💶', '💷', '🧾', '⚖️', '📜', '🖋️', '🖇️', '📌']
        },
        {
            label: 'Technologia',
            icon: '💻',
            items: ['💻', '🖥️', '⌨️', '🖱️', '📱', '📲', '🕹️', '💾', '💿', '📀', '🧮', '🔌', '🔋', '🪫', '📡', '🛰️', '🤖', '🧬', '🔬', '⚗️', '🧪', '🧫', '🧲', '⚙️', '🛠️', '🔧', '🔩', '⛓️', '🧰', '🪛', '🧑‍💻', '🖨️', '📟', '📠', '🗜️', '🧯', '🛜', '💽', '💡', '🔐', '🔒', '🔓', '🔑', '🗝️', '📶', '📳', '📴', '🔊', '🔉', '🔈', '🎛️', '🎚️', '📺', '📷', '📹', '🎥', '🔍', '🧭', '🧱', '🧩', '🪄', '🧬', '🩻', '💫', '✨', '⚡', '🔥', '🌐', '☁️']
        },
        {
            label: 'Kreatywne',
            icon: '🎨',
            items: ['🎨', '🖌️', '🖍️', '✏️', '✒️', '🖊️', '🖋️', '📐', '📏', '✂️', '🧵', '🪡', '🎭', '🎬', '🎧', '🎤', '🎹', '🥁', '🎸', '🎻', '🎲', '🧩', '🪄', '📷', '📸', '🎥', '📹', '🖼️', '🌈', '💫', '🪩', '🎼', '🎵', '🎶', '🎙️', '🎚️', '🎛️', '🪅', '🪆', '🧶', '🖋️', '🖊️', '📝', '📜', '📄', '📃', '📑', '🗒️', '🖇️', '📌', '📍', '🔖', '✨', '🌟', '⭐', '🔥', '💥', '💡', '🎞️', '📽️', '🎟️', '🎫', '🎪', '🕹️', '🎯', '🎳', '🧸', '🪀', '🪁']
        },
        {
            label: 'Status',
            icon: '⚡',
            items: ['⚡', '🔥', '⭐', '🔔', '🟢', '🟡', '🔴', '🔵', '🟣', '🟠', '⬆️', '⬇️', '➡️', '🔁', '⏳', '🚧', '🧯', '🛡️', '🏁', '🎉', '💥', '💢', '💤', '💯', '🔜', '🔝', '🆕', '🆒', '🆗', '📛', '🚨', '✅', '☑️', '❌', '❗', '❓', '♻️', '🔄', '⛔', '💬', '⭕', '🚫', '❎', '✔️', '➕', '➖', '➗', '✳️', '✴️', '🔆', '🔅', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚪', '⚫', '🟤', '🔺', '🔻', '🔸', '🔹', '🔶', '🔷', '💠', '🔰']
        },
        {
            label: 'Zespół',
            icon: '🙂',
            items: ['🙂', '😀', '😎', '🤓', '🧐', '🤩', '🥳', '🙌', '👏', '👍', '💪', '🙏', '👋', '🤝', '👥', '🧑', '👩', '👨', '🧑‍💻', '👩‍💻', '👨‍💻', '🧑‍🎨', '👩‍🔧', '👨‍🔧', '🧑‍🚀', '👩‍🏫', '👨‍🏫', '🧑‍💼', '👩‍💼', '👨‍💼', '😁', '😄', '😃', '😊', '😉', '😌', '😍', '😇', '😋', '😜', '🤠', '😺', '👌', '✌️', '🤞', '🤟', '🤘', '👊', '✊', '🫶', '🤲', '💁', '🙋', '🙆', '🙅', '🧑‍🏫', '🧑‍🔧', '🧑‍🔬', '🧑‍🚒', '🧑‍✈️', '🧑‍⚕️', '🧑‍⚖️', '🧑‍🌾']
        },
        {
            label: 'Plan',
            icon: '🗓️',
            items: ['🗓️', '📅', '📆', '⏰', '⏱️', '⏲️', '⌛', '⏳', '🕒', '📍', '🧭', '🗺️', '🧱', '🏗️', '🛤️', '🚦', '🧾', '📋', '📝', '✍️', '📌', '📎', '🔖', '🏷️', '🎯', '🏁', '🧮', '📊', '📈', '📉', '🕐', '🕑', '🕓', '🕔', '🕕', '🕖', '🕗', '🕘', '🕙', '🕚', '🕛', '📖', '📚', '🗒️', '🗂️', '🗃️', '📦', '🚧', '🔁', '🔄', '➡️', '⬅️', '⬆️', '⬇️', '🔜', '🔝', '✅', '☑️', '⚠️', '🚩']
        },
        {
            label: 'Biznes',
            icon: '💰',
            items: ['💰', '💵', '💶', '💷', '💳', '🧾', '🏦', '🏢', '🏬', '🏭', '🏗️', '🚚', '📦', '📫', '📮', '📤', '📥', '📨', '📧', '📞', '☎️', '📠', '🪪', '🧳', '🛒', '🧺', '🤝', '📊', '📈', '📉', '💸', '💎', '⚖️', '🧮', '📝', '🗂️', '📋', '📌', '🔐', '🔑', '📇', '🗃️', '🗄️', '🏷️', '📣', '📰', '🗞️', '📢', '🎯', '🏁', '🧭', '🚀', '⭐', '🏆', '✅', '📅', '⏱️', '🌐', '☁️', '🔗']
        },
        {
            label: 'Miejsca',
            icon: '🌍',
            items: ['🌍', '🌎', '🌏', '🗺️', '🏙️', '🌆', '🌃', '🏢', '🏫', '🏛️', '🏥', '🏦', '🏭', '🏗️', '⛲', '🌉', '🚉', '✈️', '🚀', '🛸', '🚗', '🚕', '🚲', '🛴', '🚢', '⚓', '🏝️', '🏕️', '🏖️', '🏜️', '🏞️', '⛰️', '🏔️', '🌋', '🗻', '🏟️', '🏰', '🗼', '🗽', '⛪', '🕌', '🛕', '🕍', '⛩️', '🕋', '⛲', '⛺', '🚏', '🚦', '🛤️', '🛣️', '🚇', '🚆', '🚊', '🚍', '🚐', '🛵']
        },
        {
            label: 'Natura',
            icon: '🌿',
            items: ['🌿', '🌱', '🌳', '🌲', '🍀', '🌵', '🌾', '🌻', '🌼', '🌸', '🌺', '🍄', '🌞', '🌙', '⭐', '🌟', '☁️', '⛅', '🌧️', '⛈️', '❄️', '💧', '🌊', '🔥', '💎', '🪨', '⛰️', '🏔️', '🌋', '🏕️', '🌷', '🪷', '💐', '🌹', '🥀', '🪻', '🌴', '🪵', '🍁', '🍂', '🍃', '🪹', '🪺', '🌑', '🌒', '🌓', '🌔', '🌕', '🌖', '🌗', '🌘', '🌈', '☀️', '🌤️', '🌦️', '🌩️', '🌨️', '🌬️', '🫧', '💦', '🧊']
        },
        {
            label: 'Jedzenie',
            icon: '🍕',
            items: ['🍕', '🍔', '🌭', '🥪', '🌮', '🌯', '🥗', '🍱', '🍜', '🍝', '🍣', '🍩', '🍪', '🍰', '🧁', '🍫', '🍿', '☕', '🍵', '🥤', '🧃', '🍎', '🍋', '🍓', '🍇', '🍉', '🥑', '🥕', '🌽', '🧀', '🥐', '🥨', '🥞', '🧇', '🥯', '🍞', '🥘', '🥫', '🍯', '🫖', '🍏', '🍐', '🍊', '🍌', '🍍', '🥭', '🍑', '🍒', '🫐', '🥝', '🍅', '🫒', '🥥', '🥦', '🥬', '🥒', '🌶️', '🫑', '🥔', '🍠', '🥜', '🫘', '🍄', '🥚', '🧈', '🥖', '🥩', '🍗', '🍖', '🍤', '🍚']
        },
        {
            label: 'Edukacja',
            icon: '🎓',
            items: ['🎓', '📚', '📖', '📕', '📗', '📘', '📙', '📓', '📒', '📝', '✏️', '🖊️', '🧮', '📐', '📏', '🔬', '🧪', '🧬', '🧫', '🌍', '🗺️', '🧠', '💡', '🏫', '👩‍🏫', '👨‍🏫', '🧑‍🏫', '🎒', '🔖', '🏅', '📔', '📒', '📄', '📃', '📑', '📊', '📈', '📉', '🗒️', '🗂️', '🖍️', '🖌️', '🖋️', '🔎', '🔍', '🧭', '⚗️', '🔭', '🪐', '🌐', '💬', '🗣️', '🎯', '🏆', '⭐', '✅', '☑️', '🧩', '🪄', '⏱️']
        },
        {
            label: 'Sport',
            icon: '🏅',
            items: ['🏅', '🏆', '🥇', '🥈', '🥉', '⚽', '🏀', '🏈', '⚾', '🎾', '🏐', '🏉', '🥏', '🎱', '🏓', '🏸', '🥊', '🥋', '⛳', '🏹', '🎣', '⛸️', '🎿', '🏂', '🏋️', '🚴', '🏃', '🏊', '🧗', '🤸', '🏌️', '🤾', '⛹️', '🤼', '🤽', '🚣', '🏄', '🛶', '🥌', '🛷', '🛼', '🛹', '🎽', '🥅', '🥎', '🏏', '🏑', '🥍', '🪃', '🎯', '🏟️', '🎟️', '📣', '🔥', '⚡', '💪', '👏', '🙌', '🏁', '🚩']
        },
        {
            label: 'Zdrowie',
            icon: '💚',
            items: ['💚', '❤️', '🩺', '💊', '🩹', '🩻', '🧬', '🧪', '🔬', '🧫', '🏥', '🚑', '🧘', '🥗', '🍎', '🥑', '💧', '🌿', '🌞', '🛌', '⏰', '🧠', '💪', '🫶', '😌', '🙂', '🌱', '🍵', '🫧', '✨', '🫀', '🫁', '🦷', '🦴', '👁️', '👂', '👃', '🧴', '🧼', '🪥', '🛁', '🚿', '🧊', '🥦', '🥬', '🥕', '🍋', '🍓', '🫐', '🥤', '🧃', '☀️', '🌈', '🌙', '⭐', '✅', '📋', '📅', '⏱️', '🔔']
        },
        {
            label: 'Symbole',
            icon: '🔣',
            items: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '☮️', '☯️', '♻️', '✅', '☑️', '✔️', '❌', '❎', '➕', '➖', '➗', '✳️', '🔆', '🔅', '🔱', '⚜️', '🔰', '⭕', '❇️', '✴️', '💠', '🔶', '🔷', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '⚫', '⚪', '🟤', '⬛', '⬜', '◼️', '◻️', '◾', '◽', '▪️', '▫️', '🔺', '🔻', '🔸', '🔹', '🔘', '🔳', '🔲', '➰', '➿', '〽️', '⚠️', '🚫']
        }
    ];
    const projectIconSetExtras = {
        'Najczęstsze': ['📁', '📂', '🗂️', '🗄️', '🗃️', '📇', '🧾', '🧮', '📜', '📄', '📃', '📑', '📒', '🗒️', '🖇️', '🧷', '🪧', '📡', '📶', '🛜', '🔋', '🔌', '💾', '💽', '🖨️', '🧑‍💻', '🧑‍🎨', '🧑‍💼', '🧑‍🔧', '🧑‍🏫', '🧑‍🔬', '💪', '🙌', '👏', '🤝', '🫶', '🚩', '⚠️', '🚨', '⛔', '⭕', '🔰', '💠', '🔶', '🔷', '🟢', '🟡', '🔴', '🟣'],
        'Praca': ['📁', '📂', '🗂️', '🗄️', '📑', '📄', '📃', '🧷', '🖊️', '✒️', '🖌️', '🔖', '🔗', '📍', '📆', '🕒', '⏳', '⌛', '🔔', '🚩', '⚠️', '🚨', '⛔', '☑️', '✔️', '❌', '🔄', '♻️', '🔎', '🔒', '🔓', '🗝️', '🏛️', '🏭', '🏗️', '🚛', '🚢', '✈️', '📦', '🧰', '🛠️', '⚙️', '💡', '🎯', '💯', '🏆', '🥇', '⭐'],
        'Technologia': ['🧑‍🔬', '🧑‍🚀', '🧑‍🔧', '🧑‍🏭', '📁', '📂', '🗂️', '🗄️', '📊', '📈', '📉', '🧾', '📋', '🖇️', '🧷', '📎', '🔖', '🏷️', '🧱', '🧰', '🪚', '🪜', '🧯', '🛡️', '🧿', '🚨', '⚠️', '✅', '☑️', '❌', '⭕', '♻️', '🔄', '🔁', '🔀', '🔂', '🔃', '⬆️', '⬇️', '➡️', '⬅️', '↗️', '↘️', '↪️', '↩️', '⏫', '⏬'],
        'Kreatywne': ['🖼️', '🪞', '🧿', '🎇', '🎆', '🌠', '🌌', '🌃', '🌆', '🌅', '🌄', '☀️', '🌙', '🌕', '🌻', '🌸', '🌺', '🌼', '🪷', '💐', '💎', '🔮', '🕯️', '🎁', '🎀', '🎊', '🎉', '🪄', '🧵', '🪡', '🧶', '🧷', '🖇️', '📎', '📚', '📖', '📕', '📗', '📘', '📙', '🧠', '💭', '💬', '🗯️', '💥', '💫', '🫧'],
        'Status': ['🟩', '🟨', '🟥', '🟦', '🟪', '🟧', '🟫', '⬛', '⬜', '◼️', '◻️', '◾', '◽', '▪️', '▫️', '🔳', '🔲', '🔘', '🔵', '🔴', '🟢', '🟡', '🟣', '🟠', '⚫', '⚪', '🟤', '🚩', '🏳️', '🏁', '📍', '📌', '🔔', '📣', '📢', '💡', '💥', '✨', '🌟', '⭐', '💯', '🔝', '🆙', '🆗', '🆕', '🆓', '🆘', '🛑'],
        'Zespół': ['😆', '🤣', '😂', '🥰', '😘', '😗', '😙', '😚', '🤗', '🤭', '🤫', '🤔', '🫡', '🤨', '😐', '😑', '😶', '🫥', '😶‍🌫️', '🙄', '😬', '😮‍💨', '🤥', '😴', '😪', '😮', '😲', '🥱', '😤', '😮‍💨', '👋', '🤚', '🖐️', '✋', '🖖', '🫱', '🫲', '🫳', '🫴', '👈', '👉', '👆', '👇', '☝️', '🫵', '🧑‍🍳', '🧑‍🎤', '🧑‍🚒'],
        'Plan': ['📌', '📍', '🧷', '🖇️', '📎', '🔖', '🏷️', '📁', '📂', '🗄️', '🗃️', '📇', '📜', '📄', '📃', '📑', '📔', '📕', '📗', '📘', '📙', '📓', '📒', '🧾', '🧮', '🔍', '🔎', '🔔', '📣', '📢', '🚨', '⛔', '⭕', '❌', '✔️', '➕', '➖', '✳️', '🔆', '🔅', '🟢', '🟡', '🔴', '🔵', '🟣', '🟠', '💯', '🎉'],
        'Biznes': ['📁', '📂', '📑', '📄', '📃', '📜', '📔', '📕', '📗', '📘', '📙', '📓', '🗒️', '🧷', '🖇️', '📎', '🔖', '🔗', '🗝️', '🔒', '🔓', '🏛️', '🏫', '🏟️', '🏪', '🏬', '🏢', '🏭', '🏗️', '🚛', '🚚', '🚢', '✈️', '🚀', '📦', '🛒', '🧺', '💡', '⚙️', '🛠️', '🧰', '📡', '📶', '🛜', '🎖️', '🏅', '🥇'],
        'Miejsca': ['🏯', '🏚️', '🏙️', '🌁', '🌄', '🌅', '🌇', '🌉', '🎠', '🛝', '🎡', '🎢', '⛱️', '🏨', '🏩', '🏪', '🏬', '🏤', '🏣', '🏦', '🏫', '🏢', '🏭', '🏗️', '🚲', '🛴', '🛵', '🏍️', '🚙', '🚎', '🚒', '🚑', '🚓', '🚕', '🚗', '🚚', '🚛', '🚜', '🚁', '🛩️', '🛫', '🛬', '🚤', '⛵', '🛳️', '🚢', '🧭', '📍'],
        'Natura': ['🌰', '🫚', '🪸', '🪨', '🪵', '🍇', '🍈', '🍉', '🍊', '🍋', '🍌', '🍍', '🥭', '🍎', '🍏', '🍐', '🍑', '🍒', '🍓', '🫐', '🥝', '🍅', '🫒', '🥥', '🥑', '🥦', '🥬', '🥒', '🌶️', '🫑', '🌽', '🥕', '🧄', '🧅', '🥔', '🍠', '🫘', '🥜', '🌍', '🌎', '🌏', '🪐', '☄️', '💫', '⚡', '🔥', '🧊', '💧'],
        'Jedzenie': ['🍛', '🍲', '🫕', '🥣', '🥡', '🥟', '🥠', '🥮', '🍢', '🍡', '🍧', '🍨', '🍦', '🥧', '🍮', '🍭', '🍬', '🍯', '🍼', '🥛', '🫗', '🍶', '🍾', '🍷', '🍸', '🍹', '🍺', '🍻', '🥂', '🥃', '🧉', '🧋', '🧊', '🥄', '🍴', '🍽️', '🥢', '🧂', '🔪', '🏺', '🛒', '🧺', '📦', '🎂', '🍥', '🍘', '🍙', '🍞'],
        'Edukacja': ['🏫', '🏛️', '🧑‍🎓', '🧑‍🏫', '🧑‍🔬', '🧑‍💻', '🧑‍🎨', '🧑‍⚖️', '🧑‍🚀', '🧑‍🔧', '🧑‍⚕️', '🧑‍💼', '📌', '📍', '📎', '🧷', '🖇️', '🔖', '🏷️', '📁', '📂', '🗄️', '🗃️', '📇', '🧾', '📜', '📰', '🗞️', '💡', '🔦', '🕯️', '🔮', '🪄', '🧿', '🎓', '🏅', '🥇', '🎖️', '🎯', '🧩', '🧱', '⚙️', '🛠️', '🔧', '📡', '🌐', '☁️', '🛜'],
        'Sport': ['🥅', '🏟️', '🎖️', '🎗️', '🎫', '🎟️', '🎪', '🎯', '🎲', '🎳', '🕹️', '🪀', '🪁', '🥁', '📣', '📢', '🔔', '🚩', '🏁', '✅', '☑️', '⭐', '🌟', '💫', '✨', '💥', '💯', '🔥', '⚡', '💪', '🦾', '🧘', '⏱️', '⏲️', '⌛', '⏳', '📊', '📈', '🏔️', '⛰️', '🏕️', '🏖️', '🌊', '☀️', '❄️', '🧊', '🎿', '🛷'],
        'Zdrowie': ['🧑‍⚕️', '👩‍⚕️', '👨‍⚕️', '🧑‍🔬', '👩‍🔬', '👨‍🔬', '🧘‍♀️', '🧘‍♂️', '🏃', '🚶', '🏋️', '🤸', '🤽', '🏊', '🚴', '🛌', '🧎', '🧍', '🍵', '🫖', '🥛', '🍼', '🧂', '🥣', '🥗', '🍯', '🍊', '🍌', '🍇', '🍉', '🥝', '🍅', '🫒', '🥥', '🥒', '🌽', '🫘', '🥜', '💚', '💙', '🤍', '💛', '🩵', '✨', '🌟', '💫', '🔆', '🔅'],
        'Dom': ['🏚️', '🏗️', '🧱', '🪵', '🪨', '🪜', '🪚', '🔨', '⛏️', '⚒️', '🛠️', '🗜️', '⛓️', '🧲', '🔌', '🔋', '🪫', '📦', '🧺', '🛒', '🛍️', '🎁', '🪑', '🛋️', '🛏️', '🚪', '🧯', '🔒', '🔓', '🗝️', '🕯️', '💡', '🔦', '📺', '📻', '🎛️', '🎚️', '🎵', '🎶', '📚', '📖', '🧸', '🧶', '🪡', '🌷', '🌼', '🌸', '🌱'],
        'Symbole': ['🟩', '🟨', '🟥', '🟦', '🟪', '🟧', '🟫', '🔶', '🔷', '🔸', '🔹', '💠', '🔘', '🔳', '🔲', '🔺', '🔻', '🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪', '❔', '❕', '❓', '❗', '‼️', '⁉️', '〰️', '➰', '➿', '🔱', '⚜️', '🔰', '♻️', '✅', '☑️', '✔️', '✖️', '❌', '⭕', '🚫', '⛔', '🛑']
    };
    projectIconSets.forEach(set => {
        set.items = [...new Set([...set.items, ...(projectIconSetExtras[set.label] || [])])];
    });
    const projectIconSetKeywords = {
        'Najczęstsze': ['popularne', 'ulubione', 'gwiazda', 'start', 'zadanie', 'projekt'],
        'Praca': ['firma', 'biuro', 'biznes', 'dokument', 'mail', 'spotkanie', 'zespół', 'zespol'],
        'Technologia': ['tech', 'komputer', 'laptop', 'telefon', 'kod', 'programowanie', 'narzędzia', 'narzedzia'],
        'Kreatywne': ['design', 'projektowanie', 'sztuka', 'muzyka', 'foto', 'kamera', 'pomysł', 'pomysl'],
        'Status': ['priorytet', 'ważne', 'wazne', 'gotowe', 'błąd', 'blad', 'alert', 'kolor'],
        'Zespół': ['ludzie', 'osoba', 'uśmiech', 'usmiech', 'team', 'człowiek', 'czlowiek'],
        'Plan': ['kalendarz', 'czas', 'termin', 'harmonogram', 'mapa', 'cel'],
        'Biznes': ['pieniądze', 'pieniadze', 'finanse', 'bank', 'sprzedaż', 'sprzedaz', 'sklep'],
        'Miejsca': ['miasto', 'budynek', 'podróż', 'podroz', 'transport', 'auto', 'samolot'],
        'Natura': ['roślina', 'roslina', 'drzewo', 'kwiat', 'pogoda', 'woda', 'ogień', 'ogien'],
        'Jedzenie': ['food', 'pizza', 'kawa', 'napój', 'napoj', 'owoc', 'warzywo'],
        'Edukacja': ['szkoła', 'szkola', 'nauka', 'książka', 'ksiazka', 'student', 'uczeń', 'uczen'],
        'Sport': ['gra', 'mecz', 'medal', 'puchar', 'piłka', 'pilka', 'trening'],
        'Zdrowie': ['medycyna', 'lekarz', 'serce', 'apteczka', 'ćwiczenia', 'cwiczenia'],
        'Symbole': ['znak', 'serce', 'kolor', 'checkbox', 'plus', 'minus', 'okrąg', 'okrag']
    };
    const projectIconKeywords = {
        '🚀': ['rakieta', 'start', 'launch'],
        '⭐': ['gwiazda', 'ulubione', 'star'],
        '✅': ['check', 'gotowe', 'zrobione', 'ok'],
        '⚙️': ['ustawienia', 'trybik', 'settings'],
        '💡': ['pomysł', 'pomysl', 'idea'],
        '📌': ['pinezka', 'przypięte', 'przypiete'],
        '📋': ['lista', 'clipboard'],
        '📁': ['folder', 'projekt'],
        '🔧': ['klucz', 'naprawa', 'narzędzie', 'narzedzie'],
        '🧩': ['puzzle', 'część', 'czesc'],
        '🎯': ['cel', 'target'],
        '📈': ['wzrost', 'wykres'],
        '🔒': ['blokada', 'zamknięte', 'zamkniete'],
        '🖥️': ['monitor', 'komputer'],
        '📱': ['telefon', 'mobile'],
        '🌐': ['internet', 'web', 'sieć', 'siec'],
        '☁️': ['chmura', 'cloud'],
        '💼': ['praca', 'teczka', 'biuro'],
        '💻': ['laptop', 'komputer', 'kod'],
        '🎨': ['sztuka', 'design', 'kolor'],
        '🙂': ['uśmiech', 'usmiech', 'osoba'],
        '🗓️': ['kalendarz', 'plan', 'termin'],
        '💰': ['pieniądze', 'pieniadze', 'finanse'],
        '🌍': ['świat', 'swiat', 'ziemia'],
        '🌿': ['natura', 'liść', 'lisc'],
        '🍕': ['pizza', 'jedzenie'],
        '🎓': ['edukacja', 'nauka'],
        '🏅': ['medal', 'sport'],
        '💚': ['zdrowie', 'serce'],
        '🔣': ['symbole', 'znaki'],
        '📅': ['data', 'kalendarz'],
        '⏰': ['alarm', 'czas'],
        '🔍': ['szukaj', 'lupa'],
        '📦': ['paczka', 'box'],
        '📝': ['notatka', 'pisanie'],
        '🏢': ['firma', 'budynek'],
        '📞': ['telefon', 'kontakt'],
        '🤝': ['współpraca', 'wspolpraca'],
        '👥': ['zespół', 'zespol', 'ludzie'],
        '🎬': ['film', 'video'],
        '🎧': ['audio', 'muzyka'],
        '📷': ['aparat', 'foto'],
        '🔥': ['ogień', 'ogien', 'pilne'],
        '🔔': ['dzwonek', 'powiadomienie'],
        '❌': ['anuluj', 'błąd', 'blad'],
        '⚠️': ['uwaga', 'ostrzeżenie', 'ostrzezenie'],
        '🏠': ['dom', 'home'],
        '❤️': ['serce', 'miłość', 'milosc']
    };
    const normalizedProjectIconSearch = projectIconSets.map(set => ({
        label: set.label,
        items: set.items.map(icon => ({
            icon,
            keywords: [
                set.label,
                ...(projectIconSetKeywords[set.label] || []),
                ...(projectIconKeywords[icon] || [])
            ].join(' ').toLowerCase()
        }))
    }));
    let activeIconPicker = null;
    let activeIconInput = null;
    let emojiPicker = null;
    let emojiPickerSearch = null;
    let emojiPickerBody = null;
    let activeIconSetIndex = 0;

    function updateProjectSubmitState() {
        if (!projectSubmitBtn || !projectNameInput) return;
        projectSubmitBtn.disabled = projectNameInput.value.trim().length === 0;
    }

    function updateTagSubmitState() {
        if (!tagSubmitBtn || !tagNameInput) return;
        tagSubmitBtn.disabled = tagNameInput.value.trim().length === 0;
    }

    function updateIssueSubmitState() {
        if (!issueSubmitBtn || !issueTitleInput) return;
        issueSubmitBtn.disabled = issueTitleInput.value.trim().length === 0;
    }

    function updateProjectRenameSubmitState() {
        if (!projectRenameSubmitBtn || !projectRenameNameInput) return;
        projectRenameSubmitBtn.disabled = projectRenameNameInput.value.trim().length === 0;
    }

    function updateSectionCreateSubmitState() {
        if (!sectionCreateSubmitBtn || !sectionCreateTitleInput) return;
        sectionCreateSubmitBtn.disabled = sectionCreateTitleInput.value.trim().length === 0;
    }

    function updateSectionRenameSubmitState() {
        if (!sectionRenameSubmitBtn || !sectionRenameTitleInput) return;
        sectionRenameSubmitBtn.disabled = sectionRenameTitleInput.value.trim().length === 0;
    }

    function closeCreateMenu() {
        if (!createMenu || !createMenuToggle) return;
        createMenu.classList.remove('is-open');
        createMenuToggle.setAttribute('aria-expanded', 'false');
    }

    function closeProjectActionMenus(exceptMenu = null) {
        projectActionMenus.forEach(menu => {
            if (menu === exceptMenu) return;
            menu.classList.remove('is-open');
            menu.querySelector('[data-project-menu-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function closeSectionActionMenu() {
        if (!sectionActionMenu) return;
        sectionActionMenu.classList.remove('is-open');
        sectionActionMenu.querySelector('[data-section-menu-toggle]')?.setAttribute('aria-expanded', 'false');
    }

    function closeStatusFilterMenu() {
        if (!statusFilterMenu || !statusFilterToggle) return;
        statusFilterMenu.classList.remove('is-open');
        statusFilterToggle.setAttribute('aria-expanded', 'false');
    }

    function closePriorityFilterMenu() {
        if (!priorityFilterMenu || !priorityFilterToggle) return;
        priorityFilterMenu.classList.remove('is-open');
        priorityFilterToggle.setAttribute('aria-expanded', 'false');
    }

    function closeInlineSelectDropdowns(exceptDropdown = null) {
        document.querySelectorAll('[data-inline-select-dropdown]').forEach(dropdown => {
            if (dropdown === exceptDropdown) return;
            dropdown.classList.remove('is-open');
            dropdown.querySelector('[data-inline-select-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function getPriorityFilterIconMarkup(priority) {
        if (!priority) return '';
        if (priority === 'urgent') {
            return '<span class="tasks-row-priority priority-urgent"><span class="tasks-priority-icon"><span class="tasks-priority-urgent-mark">!</span></span></span>';
        }
        if (priority === 'none') {
            return '<span class="tasks-row-priority priority-none"><span class="tasks-priority-icon"><span class="tasks-priority-no-mark"></span></span></span>';
        }
        return `<span class="tasks-row-priority priority-${priority}"><span class="tasks-priority-icon"><span class="tasks-priority-bars"><span></span><span></span><span></span></span></span></span>`;
    }

    function getFilterButtonText(button) {
        if (!button) return '';
        const clone = button.cloneNode(true);
        clone.querySelectorAll('[aria-hidden="true"]').forEach(node => node.remove());
        return clone.textContent.trim();
    }

    function getInlineSelect(dropdown) {
        return dropdown?.closest('.tasks-issue-select-wrap')?.querySelector('select') || null;
    }

    function syncInlineSelectDropdown(dropdown) {
        if (!dropdown) return;
        const select = getInlineSelect(dropdown);
        if (!select) return;

        const label = dropdown.querySelector('[data-inline-select-label]');
        const statusIcon = dropdown.querySelector('[data-inline-status-icon]');
        const priorityIcon = dropdown.querySelector('[data-inline-priority-icon]');
        const isMultiple = dropdown.hasAttribute('data-inline-select-multiple');
        const selectedTags = dropdown.closest('.tasks-issue-select-wrap')?.querySelector('[data-inline-selected-tags]');
        const selectedValues = Array.from(select.selectedOptions).map(option => option.value);
        const currentValue = select.value;

        dropdown.querySelectorAll('[data-inline-select-value]').forEach(button => {
            const isActive = isMultiple ? selectedValues.includes(button.dataset.inlineSelectValue) : button.dataset.inlineSelectValue === currentValue;
            button.classList.toggle('is-active', isActive);
            if (button.getAttribute('role') === 'menuitemcheckbox') {
                button.setAttribute('aria-checked', String(isActive));
            }
        });

        if (label) {
            if (isMultiple) {
                label.textContent = selectedValues.length ? `Tagi: ${selectedValues.length}` : 'Tagi';
            } else {
                const activeButton = dropdown.querySelector(`[data-inline-select-value="${currentValue}"]`);
                label.textContent = activeButton ? getFilterButtonText(activeButton) : label.textContent;
            }
        }

        if (selectedTags && isMultiple) {
            selectedTags.replaceChildren();
            dropdown.querySelectorAll('[data-inline-select-value].is-active').forEach(button => {
                const chip = button.querySelector('.tasks-tag-chip')?.cloneNode(true);
                if (chip) selectedTags.appendChild(chip);
            });
        }

        if (statusIcon) {
            statusIcon.className = `status-indicator tasks-filter-status-icon ${currentValue ? `status-${currentValue}` : 'status-label-plain'}`;
        }

        if (priorityIcon) {
            priorityIcon.innerHTML = getPriorityFilterIconMarkup(currentValue);
        }
    }

    function closeIssuePickers(exceptPicker = null) {
        [issueProjectPicker, issueSectionPicker].forEach(picker => {
            if (!picker || picker === exceptPicker) return;
            picker.classList.remove('is-open');
            picker.querySelector('[data-picker-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function normalizePickerSearch(value) {
        return (value || '').trim().toLowerCase();
    }

    function filterPickerSearch(input) {
        const query = normalizePickerSearch(input?.value);
        const type = input?.dataset.pickerSearchType || '';
        const selectedProjectId = issueProjectInput?.value || '';

        if (type === 'project') {
            issueProjectOptions.forEach(option => {
                const text = normalizePickerSearch(option.dataset.projectName || option.textContent);
                option.hidden = query ? !text.includes(query) : false;
            });
            return;
        }

        if (type === 'section') {
            issueSectionOptions.forEach(option => {
                const belongsToProject = !selectedProjectId || option.dataset.sectionProjectId === selectedProjectId;
                const text = normalizePickerSearch(option.dataset.sectionTitle || option.textContent);
                option.hidden = !belongsToProject || (query ? !text.includes(query) : false);
            });
        }
    }

    function resetPickerSearch(picker) {
        const input = picker?.querySelector('[data-picker-search]');
        if (!input) return;
        input.value = '';
        filterPickerSearch(input);
    }

    function getCollapsedProjects() {
        try {
            return new Set(JSON.parse(localStorage.getItem('collapsedTaskProjects') || '[]'));
        } catch (error) {
            return new Set();
        }
    }

    function saveCollapsedProjects(collapsedProjects) {
        try {
            localStorage.setItem('collapsedTaskProjects', JSON.stringify([...collapsedProjects]));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function getProjectTreeCollapsed() {
        try {
            return localStorage.getItem('collapsedTaskProjectTree') === 'true';
        } catch (error) {
            return false;
        }
    }

    function saveProjectTreeCollapsed(isCollapsed) {
        try {
            localStorage.setItem('collapsedTaskProjectTree', String(isCollapsed));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function setProjectTreeCollapsed(isCollapsed) {
        if (!projectTree || !projectTreeToggle) return;

        projectTree.classList.toggle('is-collapsed', isCollapsed);
        projectTreeToggle.setAttribute('aria-expanded', String(!isCollapsed));
        projectTreeToggle.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} Moje przestrzenie robocze`);
    }

    function setProjectCollapsed(projectNode, isCollapsed) {
        const toggle = projectNode.querySelector('[data-project-collapse-toggle]');
        const projectName = projectNode.querySelector('.tasks-project-title span:not(.tasks-project-badge)')?.textContent?.trim() || 'przestrzeń roboczą';

        projectNode.classList.toggle('is-collapsed', isCollapsed);
        toggle?.setAttribute('aria-expanded', String(!isCollapsed));
        toggle?.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} przestrzeń roboczą ${projectName}`);
    }

    function clearProjectTreeInitialState() {
        document.documentElement.classList.remove('tasks-project-tree-initially-collapsed');
        document.getElementById('tasks-project-tree-initial-state')?.remove();
    }

    function openModal(modal, focusTarget, onOpen) {
        if (!modal) return;
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('modal-open');
        closeCreateMenu();
        if (onOpen) onOpen();
        setTimeout(() => focusTarget?.focus(), 50);
    }

    function closeModal(modal) {
        if (!modal) return;
        closeEmojiPicker();
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        if (!document.querySelector('.tasks-modal.is-open')) {
            document.body.classList.remove('modal-open');
        }
    }

    function createSectionDefaultIconSvg() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'tasks-section-default-icon');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');

        ['M21 5.5 10 16.5 4.5 11', 'M20 12v6.5A2.5 2.5 0 0 1 17.5 21h-12A2.5 2.5 0 0 1 3 18.5v-12A2.5 2.5 0 0 1 5.5 4H15'].forEach(d => {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            svg.appendChild(path);
        });

        return svg;
    }

    function createEmptyIconSvg() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'tasks-empty-icon');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('aria-hidden', 'true');

        ['M5 5l14 14', 'M19 5 5 19'].forEach(d => {
            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', d);
            svg.appendChild(path);
        });

        return svg;
    }

    function renderProjectIcon(display, icon) {
        if (!display) return;
        display.textContent = '';
        if (!icon) {
            display.appendChild(createEmptyIconSvg());
            return;
        }
        if (icon === 'check' || icon === '✅') {
            display.appendChild(createSectionDefaultIconSvg());
            return;
        }
        display.textContent = icon;
    }

    function setIconValue(input, picker, icon) {
        const normalizedIcon = (icon || '').trim();
        if (input) input.value = normalizedIcon;
        const display = picker ? picker.querySelector('[data-selected-project-icon]') : null;
        renderProjectIcon(display, normalizedIcon);
    }

    function setIssueChip(picker, label, icon, color) {
        if (!picker) return;
        const labelEl = picker.querySelector('[data-picker-label]');
        const iconEl = picker.querySelector('[data-picker-icon]');
        const toggle = picker.querySelector('[data-picker-toggle]');

        if (labelEl) labelEl.textContent = label || '';
        if (iconEl) iconEl.textContent = icon || '';
        if (toggle && color) toggle.style.setProperty('--project-icon-fg', color);
    }

    function getSelectedSectionOption() {
        if (!issueSectionSelect?.value) return null;
        return issueSectionOptions.find(option => option.dataset.sectionId === issueSectionSelect.value) || null;
    }

    function selectIssueSection(sectionId) {
        const sectionOption = issueSectionOptions.find(option => option.dataset.sectionId === String(sectionId));
        if (!sectionOption || !issueSectionSelect) return false;

        issueSectionSelect.value = sectionOption.dataset.sectionId || '';
        setIssueChip(issueSectionPicker, sectionOption.dataset.sectionTitle || sectionCopy.emptyLabel, sectionOption.dataset.sectionIcon || '');
        return true;
    }

    function filterIssueSections(projectId) {
        let firstVisibleSectionId = '';
        const sectionSearch = issueSectionPicker?.querySelector('[data-picker-search]');
        const query = normalizePickerSearch(sectionSearch?.value);

        issueSectionOptions.forEach(option => {
            const text = normalizePickerSearch(option.dataset.sectionTitle || option.textContent);
            const isVisible = (!projectId || option.dataset.sectionProjectId === String(projectId)) && (!query || text.includes(query));
            option.hidden = !isVisible;
            if (isVisible && !firstVisibleSectionId) {
                firstVisibleSectionId = option.dataset.sectionId || '';
            }
        });

        return firstVisibleSectionId;
    }

    function selectIssueProject(projectId, preferredSectionId = '') {
        const projectOption = issueProjectOptions.find(option => option.dataset.projectId === String(projectId)) || issueProjectOptions[0];
        if (!projectOption) return;

        const selectedProjectId = projectOption.dataset.projectId || '';
        if (issueProjectInput) issueProjectInput.value = selectedProjectId;
        setIssueChip(
            issueProjectPicker,
            projectOption.dataset.projectName || 'Wybierz przestrzeń',
            projectOption.dataset.projectIcon || '',
            projectOption.dataset.projectColor || ''
        );

        const firstVisibleSectionId = filterIssueSections(selectedProjectId);
        const currentSectionOption = getSelectedSectionOption();
        const currentSectionFits = currentSectionOption?.dataset.sectionProjectId === selectedProjectId;
        const nextSectionId = preferredSectionId || (currentSectionFits ? currentSectionOption.dataset.sectionId : '') || projectOption.dataset.defaultSectionId || firstVisibleSectionId;

        if (!selectIssueSection(nextSectionId) && firstVisibleSectionId) {
            selectIssueSection(firstVisibleSectionId);
        }
    }

    function syncIssuePickers() {
        if (!issueForm || !issueProjectOptions.length) return;

        const selectedSectionOption = getSelectedSectionOption();
        const projectId = issueProjectInput?.value || selectedSectionOption?.dataset.sectionProjectId || issueProjectOptions[0]?.dataset.projectId || '';
        selectIssueProject(projectId, selectedSectionOption?.dataset.sectionId || '');
    }

    function selectIssueSectionContext(sectionId) {
        if (!sectionId) return false;
        const sectionOption = issueSectionOptions.find(option => option.dataset.sectionId === String(sectionId));
        if (!sectionOption) return false;

        selectIssueProject(sectionOption.dataset.sectionProjectId || '', sectionId);
        return true;
    }

    function setIssueStatus(status) {
        if (!issueStatusSelect || !status) return;
        const hasStatus = Array.from(issueStatusSelect.options).some(option => option.value === status);
        if (!hasStatus) return;

        issueStatusSelect.value = status;
        issueStatusSelect.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function setIssueColumn(columnId) {
        if (!issueColumnInput) return;
        issueColumnInput.value = columnId || '';
    }

    function syncProjectIconPickers() {
        projectIconGroups.forEach(group => {
            if (!group.input || !group.picker) return;
            setIconValue(group.input, group.picker, group.input.value);
        });
    }

    function getPickerForInput(input) {
        const group = projectIconGroups.find(item => item.input === input);
        return group ? group.picker : null;
    }

    function createEmojiPicker() {
        if (emojiPicker) return emojiPicker;

        emojiPicker = document.createElement('div');
        emojiPicker.className = 'tasks-emoji-picker';
        emojiPicker.setAttribute('role', 'dialog');
        emojiPicker.setAttribute('aria-label', 'Wybór ikony przestrzeni roboczej');

        const tabs = document.createElement('div');
        tabs.className = 'tasks-emoji-picker__tabs';
        projectIconSets.forEach((set, index) => {
            const tab = document.createElement('button');
            tab.type = 'button';
            tab.textContent = set.icon;
            tab.title = set.label;
            tab.setAttribute('aria-label', set.label);
            tab.addEventListener('click', () => {
                activeIconSetIndex = index;
                emojiPickerSearch.value = '';
                renderEmojiPicker();
            });
            tabs.appendChild(tab);
        });

        const searchWrap = document.createElement('div');
        searchWrap.className = 'tasks-emoji-picker__search';
        searchWrap.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="M16.5 16.5L21 21"></path></svg>';

        emojiPickerSearch = document.createElement('input');
        emojiPickerSearch.type = 'search';
        emojiPickerSearch.placeholder = 'Szukaj lub wpisz ikonę';
        emojiPickerSearch.setAttribute('aria-label', 'Szukaj ikony');
        emojiPickerSearch.addEventListener('input', renderEmojiPicker);
        searchWrap.appendChild(emojiPickerSearch);

        const clearButton = document.createElement('button');
        clearButton.type = 'button';
        clearButton.className = 'tasks-emoji-clear';
        clearButton.title = 'Usuń ikonę';
        clearButton.setAttribute('aria-label', 'Usuń ikonę');
        clearButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v5"/><path d="M14 11v5"/></svg>';
        clearButton.addEventListener('click', () => {
            setIconValue(activeIconInput, activeIconPicker, '');
            closeEmojiPicker();
            activeIconInput?.focus();
        });
        searchWrap.appendChild(clearButton);

        emojiPickerBody = document.createElement('div');
        emojiPickerBody.className = 'tasks-emoji-picker__body';

        emojiPicker.appendChild(tabs);
        emojiPicker.appendChild(searchWrap);
        emojiPicker.appendChild(emojiPickerBody);
        document.body.appendChild(emojiPicker);
        renderEmojiPicker();
        return emojiPicker;
    }

    function renderEmojiPicker() {
        if (!emojiPicker || !emojiPickerBody) return;
        const query = (emojiPickerSearch?.value || '').trim().toLowerCase();
        const tabs = emojiPicker.querySelectorAll('.tasks-emoji-picker__tabs button');
        tabs.forEach((tab, index) => tab.classList.toggle('is-active', index === activeIconSetIndex));

        emojiPickerBody.innerHTML = '';
        const searchResults = query
            ? normalizedProjectIconSearch.flatMap(set => set.items)
                .filter(item => item.icon.includes(query) || item.keywords.includes(query))
                .map(item => item.icon)
            : [];
        const sets = query
            ? [{ label: 'Wyniki', items: [...new Set(searchResults)] }]
            : [projectIconSets[activeIconSetIndex]];

        sets.forEach(set => {
            const group = document.createElement('section');
            group.className = 'tasks-emoji-group';
            const title = document.createElement('h3');
            title.textContent = set.label;
            const list = document.createElement('div');
            list.className = 'tasks-emoji-list';

            const items = set.items.length ? set.items : (query ? [query] : []);
            items.forEach(icon => {
                const option = document.createElement('button');
                option.type = 'button';
                option.className = 'tasks-emoji-option';
                option.textContent = icon;
                option.setAttribute('aria-label', `Wybierz ikonę ${icon}`);
                option.addEventListener('click', () => {
                    setIconValue(activeIconInput, activeIconPicker, icon);
                    closeEmojiPicker();
                    activeIconInput?.focus();
                });
                list.appendChild(option);
            });

            group.appendChild(title);
            group.appendChild(list);
            emojiPickerBody.appendChild(group);
        });
    }

    function openEmojiPicker(picker, input) {
        if (!picker || !input) return;
        createEmojiPicker();
        activeIconPicker = picker;
        activeIconInput = input;
        projectIconPickers.forEach(button => button.setAttribute('aria-expanded', String(button === picker)));
        emojiPickerSearch.value = '';
        renderEmojiPicker();
        emojiPicker.classList.add('is-open');
        setTimeout(() => emojiPickerSearch?.focus(), 30);
    }

    function closeEmojiPicker() {
        if (!emojiPicker) return;
        emojiPicker.classList.remove('is-open');
        projectIconPickers.forEach(button => button.setAttribute('aria-expanded', 'false'));
        activeIconPicker = null;
        activeIconInput = null;
    }

    function escapeHtml(value) {
        const div = document.createElement('div');
        div.textContent = value;
        return div.innerHTML;
    }

    if (createMenuToggle && createMenu) {
        createMenuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = createMenu.classList.toggle('is-open');
            createMenuToggle.setAttribute('aria-expanded', String(isOpen));
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
        });
    }

    if (statusFilterToggle && statusFilterMenu) {
        statusFilterToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !statusFilterMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closePriorityFilterMenu();
            statusFilterMenu.classList.toggle('is-open', isOpen);
            statusFilterToggle.setAttribute('aria-expanded', String(isOpen));
        });

        statusFilterMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    if (priorityFilterToggle && priorityFilterMenu) {
        priorityFilterToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !priorityFilterMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            priorityFilterMenu.classList.toggle('is-open', isOpen);
            priorityFilterToggle.setAttribute('aria-expanded', String(isOpen));
        });

        priorityFilterMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    document.querySelectorAll('[data-inline-select-dropdown]').forEach(dropdown => {
        const select = getInlineSelect(dropdown);
        const toggle = dropdown.querySelector('[data-inline-select-toggle]');
        const isMultiple = dropdown.hasAttribute('data-inline-select-multiple');

        syncInlineSelectDropdown(dropdown);

        toggle?.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !dropdown.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeIssuePickers();
            closeInlineSelectDropdowns(dropdown);
            dropdown.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        dropdown.querySelectorAll('[data-inline-select-value]').forEach(button => {
            button.addEventListener('click', function() {
                if (!select) return;

                if (isMultiple) {
                    const option = Array.from(select.options).find(item => item.value === this.dataset.inlineSelectValue);
                    if (option) option.selected = !option.selected;
                } else {
                    select.value = this.dataset.inlineSelectValue;
                    closeInlineSelectDropdowns();
                }

                select.dispatchEvent(new Event('change', { bubbles: true }));
                syncInlineSelectDropdown(dropdown);
            });
        });

        select?.addEventListener('change', function() {
            syncInlineSelectDropdown(dropdown);
        });
    });

    if (sectionActionMenu) {
        const toggle = sectionActionMenu.querySelector('[data-section-menu-toggle]');
        const panel = sectionActionMenu.querySelector('.tasks-section-menu');

        toggle?.addEventListener('click', function(e) {
            e.stopPropagation();
            if (!panel) return;
            if (!panel.querySelector('[role="menuitem"]:not(.u-hidden)')) return;
            const isOpen = !sectionActionMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            sectionActionMenu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        sectionActionMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    projectActionMenus.forEach(menu => {
        const toggle = menu.querySelector('[data-project-menu-toggle]');
        if (!toggle) return;

        toggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !menu.classList.contains('is-open');
            closeProjectActionMenus(menu);
            closeCreateMenu();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            menu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        menu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });

    if (projectTree && projectTreeToggle) {
        setProjectTreeCollapsed(getProjectTreeCollapsed());

        projectTreeToggle.addEventListener('click', function(e) {
            e.preventDefault();

            const isCollapsed = !projectTree.classList.contains('is-collapsed');
            setProjectTreeCollapsed(isCollapsed);
            saveProjectTreeCollapsed(isCollapsed);
        });
    }

    if (projectNodes.length) {
        const collapsedProjects = getCollapsedProjects();

        projectNodes.forEach(projectNode => {
            const projectId = projectNode.dataset.projectId || '';
            const toggle = projectNode.querySelector('[data-project-collapse-toggle]');
            const shouldCollapse = collapsedProjects.has(projectId) && !projectNode.classList.contains('is-current');

            setProjectCollapsed(projectNode, shouldCollapse);

            toggle?.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();

                const isCollapsed = !projectNode.classList.contains('is-collapsed');
                setProjectCollapsed(projectNode, isCollapsed);

                if (projectId) {
                    if (isCollapsed) {
                        collapsedProjects.add(projectId);
                    } else {
                        collapsedProjects.delete(projectId);
                    }
                    saveCollapsedProjects(collapsedProjects);
                }
            });
        });
    }

    clearProjectTreeInitialState();

    document.querySelectorAll('[data-delete-project-form]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const projectName = escapeHtml(this.dataset.projectName || 'tę przestrzeń roboczą');

            window.showConfirmModal({
                title: 'Usuń przestrzeń roboczą',
                message: `Czy na pewno chcesz usunąć przestrzeń roboczą „${projectName}”? Zadania z tej przestrzeni zostaną przeniesione do sekcji „Bez przestrzeni roboczej”.`,
                confirmText: 'Usuń przestrzeń',
                cancelText: 'Anuluj',
                confirmClass: 'btn-danger',
                onConfirm: () => this.submit()
            });
        });
    });

    openProjectButtons.forEach(button => {
        button.addEventListener('click', () => {
            openModal(projectModal, projectNameInput, updateProjectSubmitState);
        });
    });

    function setTagModalMode(mode, data = {}) {
        const isEdit = mode === 'edit';
        if (tagActionInput) tagActionInput.value = isEdit ? 'edit_tag' : 'create_tag';
        if (tagIdInput) tagIdInput.value = isEdit ? (data.tagId || '') : '';
        if (tagNameInput) tagNameInput.value = isEdit ? (data.tagName || '') : '';
        if (tagDescriptionInput) tagDescriptionInput.value = isEdit ? (data.tagDescription || '') : '';
        const tagModalTitle = document.getElementById('tag-modal-title');
        if (tagModalTitle) tagModalTitle.textContent = isEdit ? 'Edytuj tag' : 'Nowy tag';
        if (tagSubmitBtn) tagSubmitBtn.textContent = isEdit ? 'Zapisz zmiany' : 'Utwórz tag';
        updateTagSubmitState();
    }

    openTagButtons.forEach(button => {
        button.addEventListener('click', () => {
            closeCreateMenu();
            setTagModalMode('create');
            openModal(tagModal, tagNameInput, updateTagSubmitState);
        });
    });

    openProjectRenameButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (projectRenameIdInput) projectRenameIdInput.value = button.dataset.projectId || '';
            if (projectRenameNameInput) projectRenameNameInput.value = button.dataset.projectName || '';
            if (projectRenameDescriptionInput) projectRenameDescriptionInput.value = button.dataset.projectDescription || '';
            if (projectRenameCodeValue) projectRenameCodeValue.textContent = button.dataset.projectCode || '';
            if (projectRenameIconInput) projectRenameIconInput.value = button.dataset.projectIcon || '';
            syncProjectIconPickers();
            closeProjectActionMenus();
            openModal(projectRenameModal, projectRenameNameInput, updateProjectRenameSubmitState);
            setTimeout(() => projectRenameNameInput?.select(), 60);
        });
    });

    openSectionCreateButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (sectionCreateProjectInput) sectionCreateProjectInput.value = button.dataset.projectId || '';
            if (sectionCreateTitleInput) sectionCreateTitleInput.value = '';
            if (sectionCreateDescriptionInput) sectionCreateDescriptionInput.value = '';
            if (sectionCreateIconInput) sectionCreateIconInput.value = '';
            syncProjectIconPickers();
            closeProjectActionMenus();
            openModal(sectionCreateModal, sectionCreateTitleInput, updateSectionCreateSubmitState);
        });
    });

    openIssueButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (button.disabled) return;
            const sectionId = button.dataset.issueSectionId || '';
            if (!selectIssueSectionContext(sectionId)) {
                syncIssuePickers();
            }
            setIssueColumn(button.dataset.issueColumnId || '');
            setIssueStatus(button.dataset.issueStatus || '');
            openModal(issueModal, issueTitleInput, updateIssueSubmitState);
        });
    });

    issueProjectPicker?.querySelector('[data-picker-toggle]')?.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = !issueProjectPicker.classList.contains('is-open');
        closeIssuePickers(issueProjectPicker);
        issueProjectPicker.classList.toggle('is-open', isOpen);
        this.setAttribute('aria-expanded', String(isOpen));
        if (isOpen) {
            resetPickerSearch(issueProjectPicker);
            setTimeout(() => issueProjectPicker.querySelector('[data-picker-search]')?.focus(), 30);
        }
    });

    issueSectionPicker?.querySelector('[data-picker-toggle]')?.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = !issueSectionPicker.classList.contains('is-open');
        closeIssuePickers(issueSectionPicker);
        issueSectionPicker.classList.toggle('is-open', isOpen);
        this.setAttribute('aria-expanded', String(isOpen));
        if (isOpen) {
            resetPickerSearch(issueSectionPicker);
            setTimeout(() => issueSectionPicker.querySelector('[data-picker-search]')?.focus(), 30);
        }
    });

    issueProjectOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            selectIssueProject(this.dataset.projectId || '', this.dataset.defaultSectionId || '');
            closeIssuePickers();
        });
    });

    issueSectionOptions.forEach(option => {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            selectIssueProject(this.dataset.sectionProjectId || '', this.dataset.sectionId || '');
            closeIssuePickers();
        });
    });

    issuePickerSearchInputs.forEach(input => {
        input.addEventListener('click', e => e.stopPropagation());
        input.addEventListener('input', function() {
            filterPickerSearch(this);
        });
        input.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                e.stopPropagation();
                closeIssuePickers();
            }
        });
    });

    document.querySelectorAll('[data-close-modal]').forEach(button => {
        button.addEventListener('click', function() {
            closeModal(this.closest('.tasks-modal'));
        });
    });

    document.addEventListener('click', function(e) {
        if (createMenu && !createMenu.contains(e.target)) closeCreateMenu();
        if (!e.target.closest('[data-status-filter-menu]')) closeStatusFilterMenu();
        if (!e.target.closest('[data-priority-filter-menu]')) closePriorityFilterMenu();
        if (!e.target.closest('[data-section-actions]')) closeSectionActionMenu();
        if (!e.target.closest('[data-project-actions]')) closeProjectActionMenus();
        if (!e.target.closest('[data-issue-project-picker]') && !e.target.closest('[data-issue-section-picker]')) closeIssuePickers();
        if (!e.target.closest('[data-inline-select-dropdown]')) closeInlineSelectDropdowns();
        if (emojiPicker && !emojiPicker.contains(e.target) && !e.target.closest('[data-project-icon-picker]')) {
            closeEmojiPicker();
        }
    });

    if (projectNameInput) {
        projectNameInput.addEventListener('input', function() {
            updateProjectSubmitState();
        });
    }

    if (tagNameInput) {
        tagNameInput.addEventListener('input', updateTagSubmitState);
        updateTagSubmitState();
    }

    if (projectForm) {
        const codeInput = projectForm.querySelector('[name="code"]');
        if (codeInput) {
            codeInput.addEventListener('input', function() {
                codeInput.dataset.touched = 'true';
            });
        }
        if (projectIconInput && !projectIconInput.value) {
            setIconValue(projectIconInput, getPickerForInput(projectIconInput), '');
        }
        if (projectIconInput) {
            projectIconInput.addEventListener('input', function() {
                setIconValue(projectIconInput, getPickerForInput(projectIconInput), projectIconInput.value);
            });
        }
        updateProjectSubmitState();
    }

    if (projectRenameIconInput) {
        projectRenameIconInput.addEventListener('input', function() {
            setIconValue(projectRenameIconInput, getPickerForInput(projectRenameIconInput), projectRenameIconInput.value);
        });
    }

    if (sectionCreateIconInput) {
        sectionCreateIconInput.addEventListener('input', function() {
            setIconValue(sectionCreateIconInput, getPickerForInput(sectionCreateIconInput), sectionCreateIconInput.value);
        });
    }

    if (sectionRenameIconInput) {
        sectionRenameIconInput.addEventListener('input', function() {
            setIconValue(sectionRenameIconInput, getPickerForInput(sectionRenameIconInput), sectionRenameIconInput.value);
        });
    }

    syncProjectIconPickers();

    projectIconPickers.forEach(picker => {
        picker.addEventListener('click', function(e) {
            e.stopPropagation();
            const input = document.getElementById(picker.dataset.projectIconTarget || '');
            if (!input) return;
            if (emojiPicker?.classList.contains('is-open') && activeIconPicker === picker) {
                closeEmojiPicker();
                return;
            }
            openEmojiPicker(picker, input);
        });
    });

    if (issueTitleInput) {
        issueTitleInput.addEventListener('input', updateIssueSubmitState);
        updateIssueSubmitState();
    }

    if (issueSectionSelect) {
        issueSectionSelect.addEventListener('change', syncIssuePickers);
        syncIssuePickers();
    }

    if (projectRenameNameInput) {
        projectRenameNameInput.addEventListener('input', updateProjectRenameSubmitState);
        updateProjectRenameSubmitState();
    }

    if (sectionCreateTitleInput) {
        sectionCreateTitleInput.addEventListener('input', updateSectionCreateSubmitState);
        updateSectionCreateSubmitState();
    }

    if (sectionRenameTitleInput) {
        sectionRenameTitleInput.addEventListener('input', updateSectionRenameSubmitState);
        updateSectionRenameSubmitState();
    }

    document.querySelectorAll('.tasks-modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) closeModal(modal);
        });
        if (modal.classList.contains('is-open')) {
            let focusTarget = projectNameInput;
            let onOpen = updateProjectSubmitState;
            if (modal.id === 'issue-modal') {
                focusTarget = issueTitleInput;
                onOpen = updateIssueSubmitState;
            }
            if (modal.id === 'tag-modal') {
                focusTarget = tagNameInput;
                onOpen = updateTagSubmitState;
            }
            if (modal.id === 'project-rename-modal') {
                focusTarget = projectRenameNameInput;
                onOpen = updateProjectRenameSubmitState;
            }
            if (modal.id === 'section-create-modal') {
                focusTarget = sectionCreateTitleInput;
                onOpen = updateSectionCreateSubmitState;
            }
            if (modal.id === 'section-rename-modal') {
                focusTarget = sectionRenameTitleInput;
                onOpen = updateSectionRenameSubmitState;
            }
            openModal(modal, focusTarget, onOpen);
        }
    });

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeIssuePickers();
            closeEmojiPicker();
            const openModalEl = document.querySelector('.tasks-modal.is-open');
            if (openModalEl) closeModal(openModalEl);
        }
    });

    document.querySelectorAll('.tasks-toggle input').forEach(input => {
        input.addEventListener('change', function() {
            this.closest('.tasks-toggle')?.classList.toggle('is-on', this.checked);
        });
    });

    if (createMenuPanel) {
        createMenuPanel.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    function shouldIgnoreRowClick(event, row = null) {
        const cell = event.target.closest('td');
        const form = event.target.closest('form');
        const rowForm = row ? row.closest('form') : null;

        return event.target.type === 'checkbox'
            || (form && form !== rowForm)
            || event.target.closest('a, input, button, select, textarea')
            || (cell && cell.querySelector('.task-checkbox'));
    }

    // Navigate to task detail on row click
    taskRows.forEach(row => {
        row.addEventListener('click', function(e) {
            if (this.dataset.dragSuppressClick === 'true') {
                delete this.dataset.dragSuppressClick;
                return;
            }
            if (shouldIgnoreRowClick(e, this)) {
                return;
            }
            const viewUrl = this.getAttribute('data-view-url');
            if (viewUrl) {
                rememberTaskReturnPoint(viewUrl);
                window.location.href = viewUrl;
            }
        });

        row.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            if (shouldIgnoreRowClick(e, this)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (!viewUrl) return;
            e.preventDefault();
            rememberTaskReturnPoint(viewUrl);
            window.location.href = viewUrl;
        });
    });

    [...projectRows, ...sectionRows].forEach(row => {
        row.addEventListener('click', function(e) {
            if (shouldIgnoreRowClick(e, this)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (viewUrl) window.location.href = viewUrl;
        });

        row.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            if (shouldIgnoreRowClick(e, this)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (!viewUrl) return;
            e.preventDefault();
            window.location.href = viewUrl;
        });
    });

    function getDropStatus(dropTarget) {
        return dropTarget?.dataset.dropStatus || dropTarget?.closest('[data-drop-status]')?.dataset.dropStatus || '';
    }

    function getDropColumnId(dropTarget) {
        return dropTarget?.dataset.dropColumnId || dropTarget?.closest('[data-drop-column-id]')?.dataset.dropColumnId || '';
    }

    function updateTaskStatusVisual(row, status) {
        row.dataset.status = status;
        row.classList.toggle('completed', status === 'closed');

        const indicator = row.querySelector('.status-indicator');
        if (!indicator) return;

        Array.from(indicator.classList)
            .filter(className => className.startsWith('status-') && className !== 'status-indicator')
            .forEach(className => indicator.classList.remove(className));
        indicator.classList.add(`status-${status}`);
        indicator.setAttribute('aria-label', statusLabels[status] || status);
    }

    function refreshGroupCounts() {
        document.querySelectorAll('.tasks-status-block, .tasks-status-subgroup').forEach(group => {
            const count = group.querySelectorAll('.task-row').length;
            const countEl = group.querySelector(':scope > header .tasks-rail-count');
            if (countEl) countEl.textContent = count;
        });

        document.querySelectorAll('.tasks-kanban-column').forEach(column => {
            const count = column.querySelectorAll('.task-row').length;
            const countEl = column.querySelector(':scope > header .tasks-rail-count');
            if (countEl) countEl.textContent = count;
        });
    }

    function updateSubtasksCount() {
        if (!subtasksToolbar || !subtasksBoard) return;
        const title = subtasksToolbar.querySelector('.tasks-subtasks-title span');
        if (!title) return;
        title.textContent = `${taskCopy.subItems} (${subtasksBoard.querySelectorAll('.task-row').length})`;
    }

    function moveTaskRow(row, dropTarget) {
        const columnId = getDropColumnId(dropTarget);
        const status = getDropStatus(dropTarget);
        const list = dropTarget.matches('.tasks-issue-list, .tasks-status-subgroup-list')
            ? dropTarget
            : dropTarget.querySelector('.tasks-issue-list, .tasks-status-subgroup-list');
        const addCardButton = list?.querySelector(':scope > .tasks-kanban-column__add-card') || null;

        if (!row || !list) return;
        if (columnId && row.dataset.columnId === columnId) return;
        if (!columnId && (!status || row.dataset.status === status)) return;

        const previousParent = row.parentElement;
        const previousStatus = row.dataset.status;
        const previousColumnId = row.dataset.columnId || '';
        const taskId = row.dataset.taskId;

        row.dataset.dragSuppressClick = 'true';
        list.insertBefore(row, addCardButton);
        if (columnId) {
            row.dataset.columnId = columnId;
        } else {
            updateTaskStatusVisual(row, status);
        }
        refreshGroupCounts();
        applyFilters();

        fetch(`/${taskAppSegment}/update/${taskId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': window.getCookie('csrftoken')
            },
            body: JSON.stringify(columnId ? { column_id: columnId } : { status })
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok || data.status !== 'success') {
                throw new Error(data.message || 'Błąd podczas aktualizacji statusu');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (previousParent) previousParent.appendChild(row);
            row.dataset.columnId = previousColumnId;
            if (!columnId) updateTaskStatusVisual(row, previousStatus);
            refreshGroupCounts();
            applyFilters();
            showMessage(error.message || taskCopy.itemMoveError, 'error');
        });
    }

    document.querySelectorAll('.task-row[draggable="true"], .tasks-issue-row[draggable="true"]').forEach(row => {
        row.addEventListener('dragstart', function(event) {
            this.classList.add('is-dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', this.dataset.taskId || '');
        });

        row.addEventListener('dragend', function() {
            this.classList.remove('is-dragging');
            document.querySelectorAll('.is-drag-over').forEach(target => target.classList.remove('is-drag-over'));
        });
    });

    document.querySelectorAll('[data-drop-status], [data-drop-column-id]').forEach(dropTarget => {
        dropTarget.addEventListener('dragover', function(event) {
            if (!Array.from(event.dataTransfer.types).includes('text/plain')) return;
            event.preventDefault();
            event.stopPropagation();
            event.dataTransfer.dropEffect = 'move';
            document.querySelectorAll('.is-drag-over').forEach(target => {
                if (target !== this && !target.contains(this)) {
                    target.classList.remove('is-drag-over');
                }
            });
            this.classList.add('is-drag-over');
        });

        dropTarget.addEventListener('dragleave', function(event) {
            event.stopPropagation();
            if (!this.contains(event.relatedTarget)) {
                this.classList.remove('is-drag-over');
            }
        });

        dropTarget.addEventListener('drop', function(event) {
            event.preventDefault();
            event.stopPropagation();
            this.classList.remove('is-drag-over');
            const taskId = event.dataTransfer.getData('text/plain');
            const escapedTaskId = window.CSS?.escape ? CSS.escape(taskId) : taskId.replace(/["\\]/g, '\\$&');
            const row = document.querySelector(`.task-row[data-task-id="${escapedTaskId}"], .tasks-issue-row[data-task-id="${escapedTaskId}"]`);
            moveTaskRow(row, this);
        });
    });

    // Checkbox functionality
    function getSelectedTaskCheckboxes() {
        return Array.from(document.querySelectorAll('.task-checkbox:checked'))
            .filter(cb => cb.id !== 'select-all-checkbox');
    }

    function getSelectedSectionCheckbox() {
        return Array.from(sectionCheckboxes).find(cb => cb.checked) || null;
    }

    function getSelectedProjectCheckbox() {
        return Array.from(projectCheckboxes).find(cb => cb.checked) || null;
    }

    function getSelectedTagCheckbox() {
        return Array.from(tagCheckboxes).find(cb => cb.checked) || null;
    }

    function setMenuButtonState(button, isEnabled, dataset = {}) {
        if (!button) return;

        button.disabled = !isEnabled;
        Object.keys(dataset).forEach(key => {
            button.dataset[key] = dataset[key] || '';
        });
    }

    function updateDeleteMenuButtons() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        setMenuButtonState(
            editSelectedTaskMenuBtn,
            selectedTaskCheckboxes.length === 1,
            { taskId: selectedTaskCheckboxes[0]?.dataset.taskId || '' }
        );
        setMenuButtonState(
            deleteSelectedTaskMenuBtn,
            selectedTaskCheckboxes.length > 0,
            { taskCount: String(selectedTaskCheckboxes.length) }
        );

        const selectedSectionCheckbox = getSelectedSectionCheckbox();
        const sectionDataset = {
            sectionId: selectedSectionCheckbox?.dataset.sectionId || '',
            sectionTitle: selectedSectionCheckbox?.dataset.sectionTitle || '',
            sectionDescription: selectedSectionCheckbox?.dataset.sectionDescription || '',
            sectionIcon: selectedSectionCheckbox?.dataset.sectionIcon || ''
        };
        setMenuButtonState(editSelectedSectionMenuBtn, Boolean(selectedSectionCheckbox), sectionDataset);
        setMenuButtonState(
            deleteSelectedSectionMenuBtn,
            Boolean(selectedSectionCheckbox),
            sectionDataset
        );

        const selectedProjectCheckbox = getSelectedProjectCheckbox();
        const projectDataset = {
            projectId: selectedProjectCheckbox?.dataset.projectId || '',
            projectName: selectedProjectCheckbox?.dataset.projectName || '',
            projectDescription: selectedProjectCheckbox?.dataset.projectDescription || '',
            projectCode: selectedProjectCheckbox?.dataset.projectCode || '',
            projectIcon: selectedProjectCheckbox?.dataset.projectIcon || ''
        };
        setMenuButtonState(editSelectedProjectMenuBtn, Boolean(selectedProjectCheckbox), projectDataset);
        setMenuButtonState(
            deleteSelectedProjectMenuBtn,
            Boolean(selectedProjectCheckbox),
            projectDataset
        );

        const selectedTagCheckbox = getSelectedTagCheckbox();
        const tagDataset = {
            tagId: selectedTagCheckbox?.dataset.tagId || '',
            tagName: selectedTagCheckbox?.dataset.tagName || '',
            tagDescription: selectedTagCheckbox?.dataset.tagDescription || ''
        };
        setMenuButtonState(editSelectedTagMenuBtn, Boolean(selectedTagCheckbox), tagDataset);
        setMenuButtonState(
            deleteSelectedTagMenuBtn,
            Boolean(selectedTagCheckbox),
            tagDataset
        );
    }

    function updateSelection() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        const count = selectedTaskCheckboxes.length;

        if (selectedCountSpan) {
            selectedCountSpan.textContent = `${count} wybranych`;
        }

        updateDeleteMenuButtons();

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
                        statusToggleBtn.className = 'btn btn-secondary tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                            ${taskCopy.closeOne}
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
                } else {
                    row.classList.remove('checked');
                }
            }
        });

        sectionCheckboxes.forEach(cb => {
            cb.closest('.tasks-section-row')?.classList.toggle('checked', cb.checked);
        });

        projectCheckboxes.forEach(cb => {
            cb.closest('.tasks-project-row')?.classList.toggle('checked', cb.checked);
        });

        tagCheckboxes.forEach(cb => {
            cb.closest('.tasks-all-groups-row')?.classList.toggle('checked', cb.checked);
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

    sectionCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            if (this.checked) {
                sectionCheckboxes.forEach(other => {
                    if (other !== this) other.checked = false;
                });
            }
            updateSelection();
        });
    });

    projectCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            if (this.checked) {
                projectCheckboxes.forEach(other => {
                    if (other !== this) other.checked = false;
                });
            }
            updateSelection();
        });
    });

    tagCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            if (this.checked) {
                tagCheckboxes.forEach(other => {
                    if (other !== this) other.checked = false;
                });
            }
            updateSelection();
        });
    });

    // Initialize state
    updateSelection();

    function postPageAction(action, fields) {
        const form = document.createElement('form');
        form.method = 'post';
        form.style.display = 'none';

        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = window.getCookie('csrftoken');

        const actionInput = document.createElement('input');
        actionInput.type = 'hidden';
        actionInput.name = 'action';
        actionInput.value = action;

        form.append(csrfInput, actionInput);

        Object.entries(fields).forEach(([name, value]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            input.value = value;
            form.appendChild(input);
        });

        document.body.appendChild(form);
        form.submit();
    }

    function postDeleteSection(sectionId) {
        postPageAction('delete_section', { section_id: sectionId });
    }

    function postDeleteProject(projectId) {
        postPageAction('delete_project', { project_id: projectId });
    }

    function postDeleteTag(tagId) {
        postPageAction('delete_tag', { tag_id: tagId });
    }

    function editSelectedTask() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        if (selectedTaskCheckboxes.length !== 1) return;

        const taskId = selectedTaskCheckboxes[0].dataset.taskId;
        if (taskId) window.location.href = `/${taskAppSegment}/view-task/${taskId}/`;
    }

    function editSelectedSection() {
        const selectedSectionCheckbox = getSelectedSectionCheckbox();
        if (!selectedSectionCheckbox || !sectionRenameModal) return;

        if (sectionRenameIdInput) sectionRenameIdInput.value = selectedSectionCheckbox.dataset.sectionId || '';
        if (sectionRenameTitleInput) sectionRenameTitleInput.value = selectedSectionCheckbox.dataset.sectionTitle || '';
        if (sectionRenameDescriptionInput) sectionRenameDescriptionInput.value = selectedSectionCheckbox.dataset.sectionDescription || '';
        if (sectionRenameIconInput) sectionRenameIconInput.value = selectedSectionCheckbox.dataset.sectionIcon || '';
        syncProjectIconPickers();
        closeSectionActionMenu();
        openModal(sectionRenameModal, sectionRenameTitleInput, updateSectionRenameSubmitState);
        setTimeout(() => sectionRenameTitleInput?.select(), 60);
    }

    function editSelectedProject() {
        const selectedProjectCheckbox = getSelectedProjectCheckbox();
        if (!selectedProjectCheckbox || !projectRenameModal) return;

        if (projectRenameIdInput) projectRenameIdInput.value = selectedProjectCheckbox.dataset.projectId || '';
        if (projectRenameNameInput) projectRenameNameInput.value = selectedProjectCheckbox.dataset.projectName || '';
        if (projectRenameDescriptionInput) projectRenameDescriptionInput.value = selectedProjectCheckbox.dataset.projectDescription || '';
        if (projectRenameCodeValue) projectRenameCodeValue.textContent = selectedProjectCheckbox.dataset.projectCode || '';
        if (projectRenameIconInput) projectRenameIconInput.value = selectedProjectCheckbox.dataset.projectIcon || '';
        syncProjectIconPickers();
        closeSectionActionMenu();
        openModal(projectRenameModal, projectRenameNameInput, updateProjectRenameSubmitState);
        setTimeout(() => projectRenameNameInput?.select(), 60);
    }

    function editSelectedTag() {
        const selectedTagCheckbox = getSelectedTagCheckbox();
        if (!selectedTagCheckbox || !tagModal) return;

        closeSectionActionMenu();
        setTagModalMode('edit', {
            tagId: selectedTagCheckbox.dataset.tagId || '',
            tagName: selectedTagCheckbox.dataset.tagName || '',
            tagDescription: selectedTagCheckbox.dataset.tagDescription || ''
        });
        openModal(tagModal, tagNameInput, updateTagSubmitState);
        setTimeout(() => tagNameInput?.select(), 60);
    }

    function deleteSelectedSection() {
        const selectedSectionCheckbox = getSelectedSectionCheckbox();
        const sectionId = selectedSectionCheckbox?.dataset.sectionId || '';
        const sectionTitle = escapeHtml(selectedSectionCheckbox?.dataset.sectionTitle || sectionCopy.deleteFallback);
        if (!sectionId) return;

        closeSectionActionMenu();
        window.showConfirmModal({
            title: sectionCopy.deleteTitle,
            message: sectionCopy.deleteMessageTemplate.replace('{title}', sectionTitle),
            confirmText: sectionCopy.deleteConfirm,
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => postDeleteSection(sectionId)
        });
    }

    function deleteSelectedProject() {
        const selectedProjectCheckbox = getSelectedProjectCheckbox();
        const projectId = selectedProjectCheckbox?.dataset.projectId || '';
        const projectName = escapeHtml(selectedProjectCheckbox?.dataset.projectName || 'tę przestrzeń roboczą');
        if (!projectId) return;

        closeSectionActionMenu();
        window.showConfirmModal({
            title: 'Usuń przestrzeń roboczą',
            message: `Czy na pewno chcesz usunąć przestrzeń roboczą „${projectName}”? ${taskCopy.projectDeleteNote}`,
            confirmText: 'Usuń przestrzeń',
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => postDeleteProject(projectId)
        });
    }

    function deleteSelectedTag() {
        const selectedTagCheckbox = getSelectedTagCheckbox();
        const tagId = selectedTagCheckbox?.dataset.tagId || '';
        const tagName = escapeHtml(selectedTagCheckbox?.dataset.tagName || 'ten tag');
        if (!tagId) return;

        closeSectionActionMenu();
        window.showConfirmModal({
            title: 'Usuń tag',
            message: `Czy na pewno chcesz usunąć tag „${tagName}”? ${taskCopy.tagDetachNote}`,
            confirmText: 'Usuń tag',
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => postDeleteTag(tagId)
        });
    }

    function deleteSelectedTasks() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        const taskIds = selectedTaskCheckboxes.map(cb => {
            const row = cb.closest('.task-row');
            return row ? row.dataset.taskId : null;
        }).filter(id => id !== null);

        if (taskIds.length === 0) return;

        closeSectionActionMenu();
        window.showConfirmModal({
            title: 'Potwierdź usunięcie',
            message: `Czy na pewno chcesz usunąć ${taskIds.length} ${taskIds.length === 1 ? taskCopy.itemAcc : taskCopy.itemPluralGen}? Tej operacji nie można cofnąć.`,
            confirmText: 'Usuń',
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => {
                fetch(`/${taskAppSegment}/delete/`, {
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
                            cb.closest('.task-row')?.remove();
                        });
                        updateSelection();
                        refreshGroupCounts();
                        updateSubtasksCount();
                        updateGroupVisibility();
                        showMessage(data.message, 'success');
                    } else {
                        showMessage(data.message || taskCopy.itemDeleteError, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showMessage(taskCopy.itemDeleteError, 'error');
                });
            }
        });
    }

    // Edit selected task
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            editSelectedTask();
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
                    title: isClosing ? taskCopy.closeMany : taskCopy.reopenMany,
                    message: `Czy na pewno chcesz ${isClosing ? 'zamknąć' : 'ponownie otworzyć'} ${taskIds.length} ${taskIds.length === 1 ? taskCopy.itemAcc : taskCopy.itemPluralGen}?`,
                    confirmText: isClosing ? 'Zamknij' : 'Otwórz ponownie',
                    cancelText: 'Anuluj',
                    confirmClass: isClosing ? 'btn-success' : 'btn-secondary',
                    onConfirm: () => {
                        fetch(`/${taskAppSegment}/bulk-update-status/`, {
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
                                showMessage(data.message || taskCopy.itemUpdateError, 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showMessage(taskCopy.itemUpdateError, 'error');
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
            deleteSelectedTasks();
        });
    }

    if (editSelectedTaskMenuBtn) {
        editSelectedTaskMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedTask();
        });
    }

    if (editSelectedSectionMenuBtn) {
        editSelectedSectionMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedSection();
        });
    }

    if (editSelectedProjectMenuBtn) {
        editSelectedProjectMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedProject();
        });
    }

    if (editSelectedTagMenuBtn) {
        editSelectedTagMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedTag();
        });
    }

    if (deleteSelectedTaskMenuBtn) {
        deleteSelectedTaskMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            deleteSelectedTasks();
        });
    }

    if (deleteSelectedSectionMenuBtn) {
        deleteSelectedSectionMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            deleteSelectedSection();
        });
    }

    if (deleteSelectedProjectMenuBtn) {
        deleteSelectedProjectMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            deleteSelectedProject();
        });
    }

    if (deleteSelectedTagMenuBtn) {
        deleteSelectedTagMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            deleteSelectedTag();
        });
    }

    // Filtering Logic
    function currentTaskRows() {
        return document.querySelectorAll('.task-row');
    }

    function currentProjectRows() {
        return document.querySelectorAll('.tasks-project-row');
    }

    function currentSectionRows() {
        return document.querySelectorAll('.tasks-section-row');
    }

    function normalizeFilterText(value) {
        return (value || '')
            .toString()
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function rowSearchText(row) {
        return normalizeFilterText(row.dataset.searchIndex || row.textContent);
    }

    function rowPrimarySearchText(row) {
        return normalizeFilterText(row.dataset.searchPrimary || row.dataset.searchIndex || row.textContent);
    }

    function rowMatchesSearch(row, searchVal) {
        if (!searchVal) return true;
        const searchableText = searchVal.length === 1 ? rowPrimarySearchText(row) : rowSearchText(row);
        return searchableText.includes(searchVal);
    }

    function updateGroupVisibility() {
        document.querySelectorAll('.tasks-group-row').forEach(groupRow => {
            let hasVisibleTask = false;
            let nextRow = groupRow.nextElementSibling;

            while (nextRow && !nextRow.classList.contains('tasks-group-row')) {
                if (nextRow.classList.contains('task-row') && nextRow.style.display !== 'none') {
                    hasVisibleTask = true;
                    break;
                }
                nextRow = nextRow.nextElementSibling;
            }

            groupRow.style.display = hasVisibleTask ? '' : 'none';
        });

        document.querySelectorAll('.tasks-status-subgroup').forEach(group => {
            const visibleRows = Array.from(group.querySelectorAll('.task-row, .tasks-project-row, .tasks-section-row')).filter(row => row.style.display !== 'none');
            group.style.display = visibleRows.length ? '' : 'none';
        });

        document.querySelectorAll('.tasks-issue-group').forEach(group => {
            const visibleRows = Array.from(group.querySelectorAll('.task-row, .tasks-project-row, .tasks-section-row')).filter(row => row.style.display !== 'none');
            const hasEmptyState = group.querySelector('.tasks-empty-section, .tasks-empty-state') !== null;
            group.style.display = (visibleRows.length || hasEmptyState) ? '' : 'none';
        });

        document.querySelectorAll('.tasks-kanban-column').forEach(column => {
            const visibleRows = Array.from(column.querySelectorAll('.task-row')).filter(row => row.style.display !== 'none');
            column.classList.toggle('is-filter-empty', visibleRows.length === 0);
        });
    }

    function getActiveStatusFilterValue() {
        const activeStatusButton = document.querySelector('[data-status-filter].is-active');
        return filterStatus ? filterStatus.value : (activeStatusButton?.dataset.statusFilter || '');
    }

    function getActivePriorityFilterValue() {
        const activePriorityButton = document.querySelector('[data-priority-filter].is-active');
        return filterPriority ? filterPriority.value : (activePriorityButton?.dataset.priorityFilter || '');
    }

    function setActiveFilterButtons() {
        const statusVal = getActiveStatusFilterValue();
        const priorityVal = getActivePriorityFilterValue();

        filterButtons.forEach(button => {
            if (button.dataset.statusFilter !== undefined) {
                button.classList.toggle('is-active', button.dataset.statusFilter === statusVal);
            }
            if (button.dataset.priorityFilter !== undefined) {
                button.classList.toggle('is-active', button.dataset.priorityFilter === priorityVal);
            }
        });

        if (statusFilterLabel) {
            const activeStatusButton = document.querySelector(`[data-status-filter="${statusVal}"]`);
            const label = activeStatusButton && statusVal ? getFilterButtonText(activeStatusButton) : '';
            statusFilterLabel.textContent = label ? `Stan: ${label}` : 'Stan';
        }

        if (statusFilterIcon) {
            statusFilterIcon.className = `status-indicator tasks-filter-status-icon ${statusVal ? `status-${statusVal}` : 'status-label-plain'}`;
        }

        if (priorityFilterLabel) {
            const activePriorityButton = document.querySelector(`[data-priority-filter="${priorityVal}"]`);
            const label = activePriorityButton && priorityVal ? getFilterButtonText(activePriorityButton) : '';
            priorityFilterLabel.textContent = label ? `Priorytet: ${label}` : 'Priorytet';
        }

        if (priorityFilterIcon) {
            priorityFilterIcon.innerHTML = getPriorityFilterIconMarkup(priorityVal);
        }
    }

    function applyFilters() {
        const statusVal = getActiveStatusFilterValue();
        const priorityVal = getActivePriorityFilterValue();
        const activeSearch = document.getElementById('filter-search');
        const searchVal = normalizeFilterText(activeSearch ? activeSearch.value : '');

        currentTaskRows().forEach(row => {
            const rowStatus = row.getAttribute('data-status');
            const rowPriority = row.getAttribute('data-priority');
            
            const matchesStatus = !statusVal || rowStatus === statusVal;
            const matchesPriority = !priorityVal || rowPriority === priorityVal;
            const matchesSearch = rowMatchesSearch(row, searchVal);

            row.style.display = (matchesStatus && matchesPriority && matchesSearch) ? '' : 'none';
        });

        currentProjectRows().forEach(row => {
            const matchesSearch = rowMatchesSearch(row, searchVal);
            row.style.display = matchesSearch ? '' : 'none';
        });

        currentSectionRows().forEach(row => {
            const matchesSearch = rowMatchesSearch(row, searchVal);
            row.style.display = matchesSearch ? '' : 'none';
        });

        updateGroupVisibility();
        setActiveFilterButtons();
    }

    if (filterStatus) filterStatus.addEventListener('change', applyFilters);
    if (filterPriority) filterPriority.addEventListener('change', applyFilters);
    if (filterSearch) filterSearch.addEventListener('input', applyFilters);

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.dataset.statusFilter !== undefined && filterStatus) {
                filterStatus.value = this.dataset.statusFilter;
            }
            if (this.dataset.priorityFilter !== undefined && filterPriority) {
                filterPriority.value = this.dataset.priorityFilter;
            }
            if (this.dataset.statusFilter !== undefined && !filterStatus) {
                document.querySelectorAll('[data-status-filter]').forEach(btn => btn.classList.remove('is-active'));
                this.classList.add('is-active');
            }
            if (this.dataset.priorityFilter !== undefined && !filterPriority) {
                document.querySelectorAll('[data-priority-filter]').forEach(btn => btn.classList.remove('is-active'));
                this.classList.add('is-active');
            }
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            applyFilters();
        });
    });

    collapsibleGroupHeaders.forEach(header => {
        const button = header.querySelector('.tasks-group-caret');
        if (!button) return;

        button.addEventListener('click', function(event) {
            event.stopPropagation();
            const group = header.closest('.tasks-issue-group, .tasks-status-subgroup');
            if (!group) return;

            group.classList.toggle('is-collapsed');
            const isCollapsed = group.classList.contains('is-collapsed');
            button.setAttribute('aria-expanded', String(!isCollapsed));
            button.setAttribute('aria-label', isCollapsed ? 'Rozwiń sekcję' : 'Zwiń sekcję');
        });

        header.addEventListener('click', function(event) {
            if (event.target.closest('button, input, select, textarea, a')) return;
            button.click();
        });
    });

    if (subtasksCollapseButton && subtasksBoard) {
        subtasksCollapseButton.addEventListener('click', function() {
            const isCollapsed = !subtasksBoard.classList.contains('is-collapsed');
            subtasksBoard.classList.toggle('is-collapsed', isCollapsed);
            this.setAttribute('aria-expanded', String(!isCollapsed));
        });
    }

    if (subtasksSortButton && subtasksBoard) {
        subtasksSortButton.addEventListener('click', function() {
            const direction = this.dataset.sortDirection === 'asc' ? 'desc' : 'asc';
            this.dataset.sortDirection = direction;

            subtasksBoard.querySelectorAll('.tasks-issue-list').forEach(list => {
                const rows = Array.from(list.querySelectorAll('.task-row'));
                rows.sort((a, b) => {
                    const aValue = a.dataset.created || '';
                    const bValue = b.dataset.created || '';
                    return direction === 'asc' ? aValue.localeCompare(bValue) : bValue.localeCompare(aValue);
                });
                rows.forEach(row => list.appendChild(row));
            });
        });
    }

    if (subtasksDeleteButton) {
        subtasksDeleteButton.addEventListener('click', function() {
            const selectedSubtasks = subtasksBoard
                ? Array.from(subtasksBoard.querySelectorAll('.task-checkbox:checked'))
                : [];
            if (!selectedSubtasks.length) {
                showMessage(`Zaznacz ${taskCopy.subItemAcc} do usunięcia`, 'error');
                return;
            }
            deleteSelectedTasks();
        });
    }

    initIssueSidebarResize();
    applyFilters();

    // Helper functions

    function enhanceDescriptionEditor(input) {
        if (!input) return null;

        const editor = document.createElement('div');
        editor.className = `${input.className} tasks-description-editor`;
        editor.contentEditable = 'true';
        editor.setAttribute('role', 'textbox');
        editor.setAttribute('aria-multiline', 'true');
        editor.dataset.placeholder = input.getAttribute('placeholder') || '';
        editor.innerHTML = descriptionValueToEditorHtml(input.value);

        input.hidden = true;
        input.classList.add('tasks-description-source');
        input.insertAdjacentElement('afterend', editor);

        editor.addEventListener('input', function() {
            syncDescriptionInput(editor);
        });

        const form = input.closest('form');
        if (form) {
            form.addEventListener('submit', function() {
                syncDescriptionInput(editor);
            });
        }

        syncDescriptionInput(editor);
        return editor;
    }

    function initIssueSidebarResize() {
        if (!issueDetailMain || !issueSidebarResizer) return;

        const storageKey = 'tasks.issueSidebarWidth';
        const minWidth = 280;
        let width = readStoredSidebarWidth();

        if (width) {
            setSidebarWidth(width);
        }

        issueSidebarResizer.addEventListener('pointerdown', function(event) {
            if (event.button !== undefined && event.button !== 0) return;

            event.preventDefault();
            issueSidebarResizer.setPointerCapture(event.pointerId);
            issueDetailMain.classList.add('is-resizing-sidebar');
            document.body.classList.add('is-resizing-tasks-sidebar');
            updateFromPointer(event.clientX);
        });

        issueSidebarResizer.addEventListener('pointermove', function(event) {
            if (!issueDetailMain.classList.contains('is-resizing-sidebar')) return;
            updateFromPointer(event.clientX);
        });

        issueSidebarResizer.addEventListener('pointerup', finishResize);
        issueSidebarResizer.addEventListener('pointercancel', finishResize);

        issueSidebarResizer.addEventListener('keydown', function(event) {
            const step = event.shiftKey ? 48 : 24;
            const currentWidth = width || getCurrentSidebarWidth();
            let nextWidth = currentWidth;

            if (event.key === 'ArrowLeft') {
                nextWidth = currentWidth + step;
            } else if (event.key === 'ArrowRight') {
                nextWidth = currentWidth - step;
            } else if (event.key === 'Home') {
                nextWidth = minWidth;
            } else if (event.key === 'End') {
                nextWidth = getSidebarMaxWidth();
            } else {
                return;
            }

            event.preventDefault();
            setSidebarWidth(nextWidth);
            storeSidebarWidth(width);
        });

        window.addEventListener('resize', function() {
            if (!width) return;
            setSidebarWidth(width);
            storeSidebarWidth(width);
        });

        function updateFromPointer(clientX) {
            const rect = issueDetailMain.getBoundingClientRect();
            setSidebarWidth(rect.right - clientX);
        }

        function finishResize(event) {
            if (!issueDetailMain.classList.contains('is-resizing-sidebar')) return;

            issueDetailMain.classList.remove('is-resizing-sidebar');
            document.body.classList.remove('is-resizing-tasks-sidebar');
            storeSidebarWidth(width);

            if (event.pointerId !== undefined && issueSidebarResizer.hasPointerCapture(event.pointerId)) {
                issueSidebarResizer.releasePointerCapture(event.pointerId);
            }
        }

        function setSidebarWidth(nextWidth) {
            width = clampSidebarWidth(nextWidth);
            issueDetailMain.style.setProperty('--tasks-issue-sidebar-width', `${width}px`);
        }

        function getCurrentSidebarWidth() {
            const sidebar = issueDetailMain.querySelector('.tasks-issue-sidebar');
            return sidebar ? sidebar.getBoundingClientRect().width : minWidth;
        }

        function clampSidebarWidth(nextWidth) {
            return Math.round(Math.min(Math.max(Number(nextWidth) || minWidth, minWidth), getSidebarMaxWidth()));
        }

        function getSidebarMaxWidth() {
            const mainWidth = issueDetailMain.getBoundingClientRect().width || window.innerWidth;
            return Math.max(minWidth, Math.min(640, mainWidth * 0.55));
        }

        function readStoredSidebarWidth() {
            try {
                return Number(window.localStorage.getItem(storageKey)) || null;
            } catch (error) {
                return null;
            }
        }

        function storeSidebarWidth(nextWidth) {
            try {
                window.localStorage.setItem(storageKey, String(clampSidebarWidth(nextWidth)));
            } catch (error) {
                // localStorage may be unavailable in private or restricted contexts.
            }
        }
    }

    function descriptionValueToEditorHtml(value) {
        if (!value) return '';
        if (/<\/?[a-z][\s\S]*>/i.test(value)) {
            return sanitizeDescriptionHtml(value);
        }

        return plainTextToEditorHtml(value);
    }

    function plainTextToEditorHtml(value) {
        const paragraphs = value
            .split(/\n{2,}/)
            .map((paragraph) => paragraph.trim())
            .filter(Boolean)
            .map((paragraph) => `<p>${escapeHtml(paragraph).replace(/\n/g, '<br>')}</p>`);

        return paragraphs.join('');
    }

    function sanitizeDescriptionHtml(value) {
        const template = document.createElement('template');
        template.innerHTML = value;
        const allowedTags = new Set(['BR', 'DIV', 'P', 'STRONG', 'B', 'EM', 'I', 'UL', 'OL', 'LI']);

        template.content.querySelectorAll('*').forEach((element) => {
            if (!allowedTags.has(element.tagName)) {
                element.replaceWith(document.createTextNode(element.textContent || ''));
                return;
            }

            Array.from(element.attributes).forEach((attribute) => {
                element.removeAttribute(attribute.name);
            });
        });

        return template.innerHTML;
    }

    function escapeHtml(value) {
        const element = document.createElement('div');
        element.textContent = value;
        return element.innerHTML;
    }

    function syncDescriptionInput(editor) {
        if (!descriptionInput) return;
        descriptionInput.value = editor.innerHTML.trim();
        descriptionInput.dispatchEvent(new Event('input', { bubbles: true }));
    }

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
            setTimeout(() => notification.remove(), 150);
        }, 5000);
    }
}

function getTaskSortRowValue(row) {
    if (row.classList.contains('task-row')) {
        return row.dataset.created || row.dataset.taskId || '';
    }

    const title = row.querySelector('.tasks-row-title-text, .tasks-row-title, .tasks-project-row-title, .tasks-section-row-title');
    return (title ? title.textContent : row.textContent).trim().toLowerCase();
}

function sortCurrentTaskLists(direction) {
    document.querySelectorAll('.tasks-table-wrap .tasks-issue-list').forEach(list => {
        const rows = Array.from(list.children).filter(child => (
            child.classList.contains('task-row') ||
            child.classList.contains('tasks-project-row') ||
            child.classList.contains('tasks-section-row')
        ));

        if (rows.length < 2) return;

        rows.sort((a, b) => {
            const aValue = getTaskSortRowValue(a);
            const bValue = getTaskSortRowValue(b);

            return direction === 'asc'
                ? aValue.localeCompare(bValue, 'pl', { numeric: true, sensitivity: 'base' })
                : bValue.localeCompare(aValue, 'pl', { numeric: true, sensitivity: 'base' });
        });

        rows.forEach(row => list.appendChild(row));
    });
}

function updateTaskSortButton(button, direction) {
    const sortArrowHead = button.querySelector('[data-sort-arrow-head]');

    button.dataset.sortDirection = direction;
    button.setAttribute('aria-pressed', String(direction === 'asc'));
    button.setAttribute('title', direction === 'asc' ? 'Sortowanie: rosnąco' : 'Sortowanie: malejąco');
    button.setAttribute('aria-label', direction === 'asc' ? 'Sortowanie: rosnąco' : 'Sortowanie: malejąco');

    if (sortArrowHead) {
        sortArrowHead.setAttribute('d', direction === 'asc' ? 'M5 7l3-3 3 3' : 'M5 17l3 3 3-3');
    }
}

if (!window.ancoreTaskSortHandlerInitialized) {
    window.ancoreTaskSortHandlerInitialized = true;

    document.addEventListener('click', function(event) {
        const button = event.target.closest('[data-task-sort]');
        if (!button) return;

        const direction = button.dataset.sortDirection === 'asc' ? 'desc' : 'asc';
        updateTaskSortButton(button, direction);
        sortCurrentTaskLists(direction);
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTasksPage);
} else {
    initTasksPage();
}

document.addEventListener('ancore:content-loaded', initTasksPage);
