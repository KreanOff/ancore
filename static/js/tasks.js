function initTasksPage() {
    if (window.ancoreTasksPageListenersController) {
        window.ancoreTasksPageListenersController.abort();
    }

    const pageListenersController = typeof AbortController === 'function' ? new AbortController() : null;
    window.ancoreTasksPageListenersController = pageListenersController;
    const pageListenerOptions = pageListenersController ? { signal: pageListenersController.signal } : false;
    const pageCaptureListenerOptions = pageListenersController ? { signal: pageListenersController.signal, capture: true } : true;

    const taskRows = document.querySelectorAll('.task-row');
    const projectRows = document.querySelectorAll('.tasks-project-row');
    const sectionRows = document.querySelectorAll('.tasks-section-row');
    const contactsDirectoryRows = document.querySelectorAll('.contacts-directory-row');
    const projectPagination = document.querySelector('[data-project-pagination]');
    const projectPageSizeSelect = document.querySelector('[data-project-page-size]');
    const projectPageSizeDropdown = document.querySelector('[data-project-page-size-dropdown]');
    const projectPageSizeToggle = document.querySelector('[data-project-page-size-toggle]');
    const projectPageSizeLabel = document.querySelector('[data-project-page-size-label]');
    const projectPageSizeOptions = document.querySelectorAll('[data-project-page-size-value]');
    const projectPaginationSummary = document.querySelector('[data-project-pagination-summary]');
    const projectPaginationPages = document.querySelector('[data-project-pagination-pages]');
    const projectPagePrev = document.querySelector('[data-project-page-prev]');
    const projectPageNext = document.querySelector('[data-project-page-next]');
    const taskStatusPaginations = document.querySelectorAll('[data-task-status-pagination]');
    const projectSearchForm = document.querySelector('[data-project-search-form]');
    const projectSearchPageSizeInput = document.querySelector('[data-project-search-page-size]');
    const projectFilterInputs = document.querySelectorAll('[data-project-filter-input]');
    const projectFilterToggles = document.querySelectorAll('[data-project-filter-toggle]');
    const projectFilterOptions = document.querySelectorAll('[data-project-filter-option]');
    const projectFilterMenus = document.querySelectorAll('[data-project-filter-menu]');
    const projectFilterSearchInputs = document.querySelectorAll('[data-project-filter-search]');
    const projectSortMenu = document.querySelector('[data-project-sort-menu]');
    const projectSortToggle = document.querySelector('[data-project-sort-toggle]');
    const projectSortInput = document.querySelector('[data-project-sort-input]');
    const projectSortOptions = document.querySelectorAll('[data-project-sort-value]');
    const projectDefaultSort = projectSortMenu?.dataset.projectDefaultSort || 'name_asc';
    const usesServerProjectPagination = projectPagination?.dataset.serverPagination === 'true';
    const usesServerDirectoryFilters = usesServerProjectPagination || projectSearchForm?.dataset.serverDirectoryFilters === 'true';
    const deleteBtn = document.getElementById('delete-selected-btn');
    const editSelectedTaskMenuBtn = document.getElementById('edit-selected-task-menu-btn');
    const editSelectedSectionMenuBtn = document.getElementById('edit-selected-section-menu-btn');
    const infoSelectedSectionMenuBtn = document.getElementById('info-selected-section-menu-btn');
    const notesSelectedSectionMenuBtn = document.getElementById('notes-selected-section-menu-btn');
    const editSelectedProjectMenuBtn = document.getElementById('edit-selected-project-menu-btn');
    const infoSelectedProjectMenuBtn = document.getElementById('info-selected-project-menu-btn');
    const notesSelectedProjectMenuBtn = document.getElementById('notes-selected-project-menu-btn');
    const editSelectedProjectBarBtn = document.getElementById('edit-selected-project-bar-btn');
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
    const filterSearchButtons = document.querySelectorAll('[data-filter-search-submit]');
    const filterButtons = document.querySelectorAll('[data-status-filter], [data-priority-filter]');
    const statusFilterMenu = document.querySelector('[data-status-filter-menu]');
    const statusFilterToggle = document.querySelector('[data-status-filter-toggle]');
    const statusFilterLabel = document.querySelector('[data-status-filter-label]');
    const statusFilterIcon = document.querySelector('[data-status-filter-icon]');
    const priorityFilterMenu = document.querySelector('[data-priority-filter-menu]');
    const priorityFilterToggle = document.querySelector('[data-priority-filter-toggle]');
    const priorityFilterLabel = document.querySelector('[data-priority-filter-label]');
    const priorityFilterIcon = document.querySelector('[data-priority-filter-icon]');
    const directoryMembersMenus = document.querySelectorAll('[data-directory-members-menu]');
    const directoryMembersSearchInputs = document.querySelectorAll('[data-directory-members-search]');
    const directoryShareButtons = document.querySelectorAll('[data-directory-share-open]:not([data-directory-members-toggle])');
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
    const selectAllCheckbox = document.querySelector('[data-select-all-checkbox], #select-all-checkbox');
    const checkboxes = document.querySelectorAll('.task-checkbox');
    const sectionCheckboxes = document.querySelectorAll('.tasks-section-row .tasks-row-checkbox[data-section-id]');
    const projectCheckboxes = document.querySelectorAll('.tasks-row-checkbox[data-project-id]');
    const tagCheckboxes = document.querySelectorAll('.tasks-row-checkbox[data-tag-id]');
    const contactCheckboxes = document.querySelectorAll('.tasks-row-checkbox[data-contact-id]');
    const companyCheckboxes = document.querySelectorAll('.tasks-row-checkbox[data-company-id]');
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
    const railNavGroups = document.querySelectorAll('[data-rail-nav-group]');
    const projectNodes = document.querySelectorAll('[data-project-node]');
    const openProjectButtons = document.querySelectorAll('[data-open-project]');
    const openTagButtons = document.querySelectorAll('[data-open-tag]');
    const openTagEditButtons = document.querySelectorAll('[data-open-tag-edit]');
    const openTagInfoButtons = document.querySelectorAll('[data-open-tag-info]');
    const openTagNotesButtons = document.querySelectorAll('[data-open-tag-notes]');
    const openProjectRenameButtons = document.querySelectorAll('[data-open-project-rename]');
    const openProjectInfoButtons = document.querySelectorAll('[data-open-project-info]');
    const openProjectNotesButtons = document.querySelectorAll('[data-open-project-notes]');
    const openSectionNotesButtons = document.querySelectorAll('[data-open-section-notes]');
    const openSectionInfoButtons = document.querySelectorAll('[data-open-section-info]');
    const openSectionRenameButtons = document.querySelectorAll('[data-open-section-rename]');
    const openSectionCreateButtons = document.querySelectorAll('[data-open-section-create]');
    const openIssueButtons = document.querySelectorAll('#open-issue-modal, [data-open-issue]');
    const openContactButtons = document.querySelectorAll('[data-open-contact]');
    const openCompanyButtons = document.querySelectorAll('[data-open-company]');
    const projectModal = document.getElementById('project-modal');
    const tagModal = document.getElementById('tag-modal');
    const projectRenameModal = document.getElementById('project-rename-modal');
    const projectNotesModal = document.getElementById('project-notes-modal');
    const sectionNotesModal = document.getElementById('section-notes-modal');
    const tagNotesModal = document.getElementById('tag-notes-modal');
    const projectInfoModal = document.getElementById('project-info-modal');
    const projectInfoBody = projectInfoModal?.querySelector('[data-project-info-body]');
    const projectInfoTitle = projectInfoModal?.querySelector('[data-project-info-title]');
    const projectInfoName = projectInfoModal?.querySelector('[data-project-info-name]');
    const projectInfoCode = projectInfoModal?.querySelector('[data-project-info-code]');
    const projectInfoDescription = projectInfoModal?.querySelector('[data-project-info-description]');
    const projectInfoProgress = projectInfoModal?.querySelector('[data-project-info-progress]');
    const projectInfoProgressFill = projectInfoModal?.querySelector('[data-project-info-progress-fill]');
    const projectInfoProgressValue = projectInfoModal?.querySelector('[data-project-info-progress-value]');
    const projectInfoTasks = projectInfoModal?.querySelector('[data-project-info-tasks]');
    const projectInfoTagCategory = projectInfoModal?.querySelector('[data-project-info-tag-category]');
    const projectInfoTagVisual = projectInfoModal?.querySelector('[data-project-info-tag-visual]');
    const projectInfoTagScope = projectInfoModal?.querySelector('[data-project-info-tag-scope]');
    const projectInfoTagOwner = projectInfoModal?.querySelector('[data-project-info-tag-owner]');
    const projectInfoTagUsage = projectInfoModal?.querySelector('[data-project-info-tag-usage]');
    const projectInfoTagAutomation = projectInfoModal?.querySelector('[data-project-info-tag-automation]');
    const projectInfoTagRelated = projectInfoModal?.querySelector('[data-project-info-tag-related]');
    const projectInfoStatus = projectInfoModal?.querySelector('[data-project-info-status]');
    const projectInfoStage = projectInfoModal?.querySelector('[data-project-info-stage]');
    const projectInfoHealth = projectInfoModal?.querySelector('[data-project-info-health]');
    const projectInfoCompany = projectInfoModal?.querySelector('[data-project-info-company]');
    const projectInfoResponsible = projectInfoModal?.querySelector('[data-project-info-responsible]');
    const projectInfoPriority = projectInfoModal?.querySelector('[data-project-info-priority]');
    const projectInfoStart = projectInfoModal?.querySelector('[data-project-info-start]');
    const projectInfoDue = projectInfoModal?.querySelector('[data-project-info-due]');
    const projectInfoBudget = projectInfoModal?.querySelector('[data-project-info-budget]');
    const projectInfoSource = projectInfoModal?.querySelector('[data-project-info-source]');
    const projectInfoCreated = projectInfoModal?.querySelector('[data-project-info-created]');
    const projectInfoLastActivity = projectInfoModal?.querySelector('[data-project-info-last-activity]');
    const projectInfoRows = {
        code: projectInfoCode?.closest('div'),
        progress: projectInfoProgress?.closest('div'),
        tasks: projectInfoTasks?.closest('div'),
        tagCategory: projectInfoTagCategory?.closest('div'),
        tagVisual: projectInfoTagVisual?.closest('div'),
        tagScope: projectInfoTagScope?.closest('div'),
        tagOwner: projectInfoTagOwner?.closest('div'),
        tagUsage: projectInfoTagUsage?.closest('div'),
        tagAutomation: projectInfoTagAutomation?.closest('div'),
        tagRelated: projectInfoTagRelated?.closest('div'),
        status: projectInfoStatus?.closest('div'),
        stage: projectInfoStage?.closest('div'),
        health: projectInfoHealth?.closest('div'),
        company: projectInfoCompany?.closest('div'),
        responsible: projectInfoResponsible?.closest('div'),
        priority: projectInfoPriority?.closest('div'),
        start: projectInfoStart?.closest('div'),
        due: projectInfoDue?.closest('div'),
        budget: projectInfoBudget?.closest('div'),
        source: projectInfoSource?.closest('div'),
        created: projectInfoCreated?.closest('div'),
        lastActivity: projectInfoLastActivity?.closest('div')
    };
    const sectionCreateModal = document.getElementById('section-create-modal');
    const sectionRenameModal = document.getElementById('section-rename-modal');
    const issueModal = document.getElementById('issue-modal');
    const directoryShareModal = document.getElementById('directory-share-modal');
    const contactCreateModal = document.getElementById('contact-create-modal');
    const companyCreateModal = document.getElementById('company-create-modal');
    const projectForm = document.getElementById('project-create-form');
    const tagForm = document.getElementById('tag-create-form');
    const projectRenameForm = document.getElementById('project-rename-form');
    const projectNotesForm = document.getElementById('project-notes-form');
    const sectionNotesForm = document.getElementById('section-notes-form');
    const tagNotesForm = document.getElementById('tag-notes-form');
    const sectionCreateForm = document.getElementById('section-create-form');
    const sectionRenameForm = document.getElementById('section-rename-form');
    const issueForm = document.getElementById('issue-create-form');
    const directoryShareForm = document.getElementById('directory-share-form');
    const contactCreateForm = document.getElementById('contact-create-form');
    const companyCreateForm = document.getElementById('company-create-form');
    const projectNameInput = projectForm ? projectForm.querySelector('[name="name"]') : null;
    const tagActionInput = tagForm ? tagForm.querySelector('[name="action"]') : null;
    const tagIdInput = tagForm ? tagForm.querySelector('[name="tag_id"]') : null;
    const tagNameInput = tagForm ? tagForm.querySelector('[name="name"]') : null;
    const tagDescriptionInput = tagForm ? tagForm.querySelector('[name="description"]') : null;
    const tagCategoryInput = tagForm ? tagForm.querySelector('[name="category"]') : null;
    const tagColorInput = tagForm ? tagForm.querySelector('[name="color"]') : null;
    const tagIconInput = tagForm ? tagForm.querySelector('[name="icon"]') : null;
    const tagPriorityInput = tagForm ? tagForm.querySelector('[name="priority"]') : null;
    const tagScopeInput = tagForm ? tagForm.querySelector('[name="scope"]') : null;
    const tagOwnerInput = tagForm ? tagForm.querySelector('[name="owner_label"]') : null;
    const tagStatusInput = tagForm ? tagForm.querySelector('[name="status"]') : null;
    const tagUsageNotesInput = tagForm ? tagForm.querySelector('[name="usage_notes"]') : null;
    const tagAutomationRulesInput = tagForm ? tagForm.querySelector('[name="automation_rules"]') : null;
    const tagRelatedTagsInput = tagForm ? tagForm.querySelector('[name="related_tags"]') : null;
    const projectRenameNameInput = projectRenameForm ? projectRenameForm.querySelector('[name="name"]') : null;
    const projectRenameDescriptionInput = projectRenameForm ? projectRenameForm.querySelector('[name="description"]') : null;
    const projectNotesIdInput = projectNotesForm ? projectNotesForm.querySelector('[data-project-notes-id]') : null;
    const projectNotesNameInput = projectNotesModal ? projectNotesModal.querySelector('[data-project-notes-name]') : null;
    const projectNotesMessageInput = projectNotesForm ? projectNotesForm.querySelector('[data-project-notes-message]') : null;
    const projectNotesThreads = projectNotesModal ? projectNotesModal.querySelectorAll('[data-project-notes-thread]') : [];
    const sectionNotesIdInput = sectionNotesForm ? sectionNotesForm.querySelector('[data-section-notes-id]') : null;
    const sectionNotesNameInput = sectionNotesModal ? sectionNotesModal.querySelector('[data-section-notes-name]') : null;
    const sectionNotesMessageInput = sectionNotesForm ? sectionNotesForm.querySelector('[data-section-notes-message]') : null;
    const sectionNotesThreads = sectionNotesModal ? sectionNotesModal.querySelectorAll('[data-section-notes-thread]') : [];
    const tagNotesIdInput = tagNotesForm ? tagNotesForm.querySelector('[data-tag-notes-id]') : null;
    const tagNotesNameInput = tagNotesModal ? tagNotesModal.querySelector('[data-tag-notes-name]') : null;
    const tagNotesMessageInput = tagNotesForm ? tagNotesForm.querySelector('[data-tag-notes-message]') : null;
    const tagNotesThreads = tagNotesModal ? tagNotesModal.querySelectorAll('[data-tag-notes-thread]') : [];
    const projectRenameCompanyInput = projectRenameForm ? projectRenameForm.querySelector('[name="company"]') : null;
    const projectRenameResponsibleInput = projectRenameForm ? projectRenameForm.querySelector('[name="responsible_user"]') : null;
    const projectRenameStatusInput = projectRenameForm ? projectRenameForm.querySelector('[name="status"]') : null;
    const projectRenameStageInput = projectRenameForm ? projectRenameForm.querySelector('[name="stage"]') : null;
    const projectRenameHealthInput = projectRenameForm ? projectRenameForm.querySelector('[name="health"]') : null;
    const projectRenamePriorityInput = projectRenameForm ? projectRenameForm.querySelector('[name="priority"]') : null;
    const projectRenameStartAtInput = projectRenameForm ? projectRenameForm.querySelector('[name="start_at"]') : null;
    const projectRenameDueAtInput = projectRenameForm ? projectRenameForm.querySelector('[name="due_at"]') : null;
    const projectRenameBudgetInput = projectRenameForm ? projectRenameForm.querySelector('[name="budget_amount"]') : null;
    const projectRenameCurrencyInput = projectRenameForm ? projectRenameForm.querySelector('[name="currency"]') : null;
    const projectRenameSourceInput = projectRenameForm ? projectRenameForm.querySelector('[name="source"]') : null;
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
    const projectTreeStorageKey = taskAppSegment === 'kanban' ? 'collapsedKanbanProjectTree' : 'collapsedTaskProjectTree';
    const collapsedProjectsStorageKey = taskAppSegment === 'kanban' ? 'collapsedKanbanProjects' : 'collapsedTaskProjects';
    const projectPageSizes = [10, 25, 50, 100, 150, 200];
    let projectSearchDebounceTimer = null;
    let projectPaginationPage = Number.parseInt(projectPagination?.dataset.projectCurrentPage || '1', 10);
    if (!Number.isFinite(projectPaginationPage) || projectPaginationPage < 1) {
        projectPaginationPage = 1;
    }

    initKanbanColumnCreateForms();
    initKanbanColumnReorder();
    initKanbanWallpapers();
    initDirectoryColumnResize();

    function navigateWithinApp(viewUrl) {
        if (window.AncoreApp?.canNavigatePartially?.(viewUrl)) {
            window.AncoreApp.navigate(viewUrl);
            return;
        }

        window.location.href = viewUrl;
    }

    function taskStatusBlockSelector(block) {
        if (block?.id && window.CSS?.escape) {
            return `#${CSS.escape(block.id)}`;
        }
        if (block?.id) {
            return `#${block.id}`;
        }

        const status = block?.dataset.sectionStatus || '';
        if (status && window.CSS?.escape) {
            return `.tasks-status-block[data-section-status="${CSS.escape(status)}"]`;
        }
        if (status) {
            return `.tasks-status-block[data-section-status="${status}"]`;
        }

        return '';
    }

    function preserveTaskStatusBlockState(fromBlock, toBlock) {
        if (!fromBlock || !toBlock) return;

        const isCollapsed = fromBlock.classList.contains('is-collapsed');
        toBlock.classList.toggle('is-collapsed', isCollapsed);
        const caret = toBlock.querySelector('.tasks-group-caret');
        if (caret) {
            caret.setAttribute('aria-expanded', String(!isCollapsed));
            caret.setAttribute('aria-label', isCollapsed ? 'Rozwiń sekcję' : 'Zwiń sekcję');
        }
    }

    async function navigateTaskStatusPage(viewUrl, pagination) {
        const currentBlock = pagination?.closest('.tasks-status-block');
        const selector = taskStatusBlockSelector(currentBlock);
        const url = (() => {
            try {
                return new URL(viewUrl, window.location.href);
            } catch (error) {
                return null;
            }
        })();

        if (!currentBlock || !selector || !url || url.origin !== window.location.origin) {
            navigateWithinApp(viewUrl);
            return;
        }

        if (window.ancoreTaskStatusPaginationController) {
            window.ancoreTaskStatusPaginationController.abort();
        }

        const controller = typeof AbortController === 'function' ? new AbortController() : null;
        window.ancoreTaskStatusPaginationController = controller;
        currentBlock.setAttribute('aria-busy', 'true');

        try {
            const requestOptions = {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'text/html',
                },
                credentials: 'same-origin',
            };

            if (controller) {
                requestOptions.signal = controller.signal;
            }

            const response = await fetch(url.href, requestOptions);
            if (!response.ok) {
                navigateWithinApp(url.href);
                return;
            }

            const html = await response.text();
            const nextDocument = new DOMParser().parseFromString(html, 'text/html');
            const nextBlock = nextDocument.querySelector(selector);

            if (!nextBlock) {
                navigateWithinApp(url.href);
                return;
            }

            const replacement = nextBlock.cloneNode(true);
            preserveTaskStatusBlockState(currentBlock, replacement);
            currentBlock.replaceWith(replacement);

            const responseUrl = response.url || url.href;
            window.history.pushState({ ancorePartialNavigation: true }, '', responseUrl);
            window.AncoreIcons?.render(replacement);
            document.dispatchEvent(new CustomEvent('ancore:content-loaded', {
                detail: {
                    url: responseUrl,
                    partial: 'task-status-pagination',
                    statusBlock: replacement.id || replacement.dataset.sectionStatus || '',
                },
            }));
        } catch (error) {
            if (error.name !== 'AbortError') {
                navigateWithinApp(url.href);
            }
        } finally {
            if (!controller || window.ancoreTaskStatusPaginationController === controller) {
                window.ancoreTaskStatusPaginationController = null;
            }
            currentBlock.removeAttribute('aria-busy');
        }
    }

    function projectWindowUrl(extraParams = {}) {
        const url = new URL(projectSearchForm?.getAttribute('action') || window.location.pathname, window.location.origin);
        const formData = projectSearchForm ? new FormData(projectSearchForm) : null;
        const currentUrl = new URL(window.location.href);
        const viewValue = (formData?.get('view') || currentUrl.searchParams.get('view') || '').toString();
        const projectValue = (formData?.get('project') || currentUrl.searchParams.get('project') || '').toString();
        const searchValue = filterSearch?.value?.trim() || '';
        const priorityValue = filterPriority?.value || '';
        const pageSizeValue = projectPageSizeSelect ? String(getProjectPageSize()) : (projectSearchPageSizeInput?.value || '');

        ['after', 'before', 'page'].forEach(param => {
            url.searchParams.delete(param);
        });
        currentUrl.searchParams.forEach((value, key) => {
            if (/^task_[a-z_]+_page_size$/.test(key)) {
                url.searchParams.set(key, value);
            }
        });
        Array.from(url.searchParams.keys()).forEach(key => {
            if (/^task_[a-z_]+_page$/.test(key)) {
                url.searchParams.delete(key);
            }
        });

        if (viewValue) {
            url.searchParams.set('view', viewValue);
            url.searchParams.delete('project');
        } else if (projectValue) {
            url.searchParams.set('project', projectValue);
            url.searchParams.delete('view');
        } else {
            url.searchParams.delete('view');
            url.searchParams.delete('project');
        }
        if (searchValue) {
            url.searchParams.set('q', searchValue);
        } else {
            url.searchParams.delete('q');
        }
        if (priorityValue) {
            url.searchParams.set('priority', priorityValue);
        } else {
            url.searchParams.delete('priority');
        }
        projectFilterInputs.forEach(input => {
            const name = input.getAttribute('name') || '';
            if (!name) return;
            const value = input.value || '';
            if (value) {
                url.searchParams.set(name, value);
            } else {
                url.searchParams.delete(name);
            }
        });
        if (projectSortInput) {
            const sortValue = projectSortInput.value || '';
            if (sortValue) {
                url.searchParams.set('sort', sortValue);
            } else {
                url.searchParams.delete('sort');
            }
        }
        if (projectPageSizeSelect || projectSearchPageSizeInput) {
            if (pageSizeValue) {
                url.searchParams.set('page_size', pageSizeValue);
            } else {
                url.searchParams.delete('page_size');
            }
        } else {
            url.searchParams.delete('page_size');
        }

        Object.entries(extraParams).forEach(([key, value]) => {
            if (value) {
                url.searchParams.set(key, value);
            } else {
                url.searchParams.delete(key);
            }
        });

        return `${url.pathname}${url.search}`;
    }

    function navigateProjectWindow(extraParams = {}) {
        if (projectSearchPageSizeInput) {
            projectSearchPageSizeInput.value = String(getProjectPageSize());
        }
        navigateWithinApp(projectWindowUrl(extraParams));
    }

    function initKanbanWallpapers() {
        const panel = document.querySelector('[data-kanban-wallpaper-panel]');
        const toggle = document.querySelector('[data-kanban-wallpaper-toggle]');
        const closeButton = document.querySelector('[data-kanban-wallpaper-close]');
        const input = document.querySelector('[data-kanban-wallpaper-input]');
        const list = document.querySelector('[data-kanban-wallpaper-list]');
        const clearButton = document.querySelector('[data-kanban-wallpaper-clear]');
        const boards = document.querySelectorAll('.tasks-kanban-board');

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

        function applyWallpaperPreviews() {
            const wallpapers = readWallpapers();

            document.querySelectorAll('[data-kanban-wallpaper-key]').forEach(card => {
                const preview = card.querySelector('[data-kanban-wallpaper-preview]');
                const boardPath = card.dataset.kanbanWallpaperKey || '';
                let selectedId = '';

                try {
                    selectedId = boardPath ? localStorage.getItem(`ancore:kanban:wallpaper:${boardPath}`) || '' : '';
                } catch (error) {
                    selectedId = '';
                }

                const selected = wallpapers.find(wallpaper => wallpaper.id === selectedId);

                if (preview && selected?.dataUrl) {
                    preview.style.backgroundImage = `url("${selected.dataUrl}")`;
                    preview.classList.add('has-wallpaper');
                } else if (preview) {
                    preview.style.backgroundImage = '';
                    preview.classList.remove('has-wallpaper');
                }
            });
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

        applyWallpaperPreviews();

        if (!boards.length) return;

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
                    applyWallpaperPreviews();
                    renderWallpapers();
                });

                const remove = document.createElement('button');
                remove.type = 'button';
                remove.className = 'tasks-kanban-wallpaper-swatch__remove';
                remove.innerHTML = window.AncoreIcons
                    ? window.AncoreIcons.html('x')
                    : '<i data-lucide="x" aria-hidden="true"></i>';
                renderLucideIcons(remove);
                remove.setAttribute('aria-label', 'Usuń tapetę');
                remove.addEventListener('click', event => {
                    event.stopPropagation();
                    const nextWallpapers = readWallpapers().filter(item => item.id !== wallpaper.id);
                    if (!writeWallpapers(nextWallpapers)) return;
                    if (getSelectedWallpaperId() === wallpaper.id) {
                        setSelectedWallpaperId('');
                        applyWallpaper();
                    }
                    applyWallpaperPreviews();
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
            applyWallpaperPreviews();
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
                applyWallpaperPreviews();
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
    const sectionCreateCodeInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="code"]') : null;
    const sectionCreateProjectInput = sectionCreateForm ? sectionCreateForm.querySelector('input[name="project_id"]') : null;
    const sectionCreateProjectSelect = sectionCreateForm ? sectionCreateForm.querySelector('[data-section-create-project-select]') : null;
    const sectionCreateKindInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="kind"]') : null;
    const sectionCreateStatusInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="status"]') : null;
    const sectionCreateOwnerInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="owner"]') : null;
    const sectionCreatePriorityInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="priority"]') : null;
    const sectionCreateDueAtInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="due_at"]') : null;
    const sectionCreateWipLimitInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="wip_limit"]') : null;
    const sectionCreateIconInput = sectionCreateForm ? sectionCreateForm.querySelector('[name="icon"]') : null;
    const sectionRenameTitleInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="title"]') : null;
    const sectionRenameDescriptionInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="description"]') : null;
    const sectionRenameCodeInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="code"]') : null;
    const sectionRenameKindInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="kind"]') : null;
    const sectionRenameStatusInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="status"]') : null;
    const sectionRenameOwnerInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="owner"]') : null;
    const sectionRenamePriorityInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="priority"]') : null;
    const sectionRenameDueAtInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="due_at"]') : null;
    const sectionRenameWipLimitInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="wip_limit"]') : null;
    const sectionRenameIconInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="icon"]') : null;
    const sectionRenameIdInput = sectionRenameForm ? sectionRenameForm.querySelector('[name="section_id"]') : null;
    const issueTitleInput = issueForm ? issueForm.querySelector('[name="title"]') : null;
    const issueProjectInput = issueForm ? issueForm.querySelector('[name="project_id"]') : null;
    const issueColumnInput = issueForm ? issueForm.querySelector('[name="column_id"]') : null;
    const issueSectionSelect = issueForm ? issueForm.querySelector('[name="section"]') : null;
    const issueStatusSelect = issueForm ? issueForm.querySelector('[name="status"]') : null;
    const issueBillableInput = issueForm ? issueForm.querySelector('[name="is_billable"]') : null;
    const issueProjectPicker = issueForm ? issueForm.querySelector('[data-issue-project-picker]') : null;
    const issueSectionPicker = issueForm ? issueForm.querySelector('[data-issue-section-picker]') : null;
    let issueProjectOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-project-option]')) : [];
    let issueSectionOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-section-option]')) : [];
    const issuePickerSearchInputs = issueForm ? Array.from(issueForm.querySelectorAll('[data-picker-search]')) : [];
    const issuePickerSearchButtons = issueForm ? Array.from(issueForm.querySelectorAll('[data-picker-search-submit]')) : [];
    const issuePickerOptionsData = parseIssuePickerOptions();
    const issueSectionOptionsData = issuePickerOptionsData.flatMap(project => project.sections || []);
    let issuePickerOptionsHydrated = false;
    const directoryShareActionInput = directoryShareForm ? directoryShareForm.querySelector('[name="action"]') : null;
    const directoryShareProjectInput = directoryShareForm ? directoryShareForm.querySelector('[name="project_id"]') : null;
    const directoryShareSectionInput = directoryShareForm ? directoryShareForm.querySelector('[name="section_id"]') : null;
    const directoryShareTaskInput = directoryShareForm ? directoryShareForm.querySelector('[name="task_id"]') : null;
    const directoryShareMemberIdInput = directoryShareForm ? directoryShareForm.querySelector('[name="member_id"]') : null;
    const directoryShareObjectTypeInput = directoryShareForm ? directoryShareForm.querySelector('[name="share_object_type"]') : null;
    const directoryShareObjectIdInput = directoryShareForm ? directoryShareForm.querySelector('[name="share_object_id"]') : null;
    const directoryShareMemberInput = directoryShareForm ? directoryShareForm.querySelector('[name="member_query"]') : null;
    const directoryShareSelectedInput = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-selected-input]') : null;
    const directorySharePermissionInput = directoryShareForm ? directoryShareForm.querySelector('[name="permission"]') : null;
    const directorySharePersonInputs = [directoryShareMemberInput].filter(Boolean);
    const directoryShareContext = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-context]') : null;
    const directoryShareResults = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-results]') : null;
    const directoryShareResultOptions = directoryShareForm ? Array.from(directoryShareForm.querySelectorAll('[data-directory-share-result]')) : [];
    const directoryShareResultsEmpty = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-results-empty]') : null;
    const directoryShareContactOptions = directoryShareForm ? Array.from(directoryShareForm.querySelectorAll('[data-directory-share-contact]')) : [];
    const directorySharePickOptions = directoryShareForm ? Array.from(directoryShareForm.querySelectorAll('[data-directory-share-pick]')) : [];
    const directoryShareContactsEmpty = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-contacts-empty]') : null;
    const directoryShareSharedList = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-shared-list]') : null;
    const directoryShareSharedEmpty = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-shared-empty]') : null;
    const directoryShareSharedCount = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-shared-count]') : null;
    const directoryShareLinkInput = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-link-input]') : null;
    const directoryShareLinkCreateBtn = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-link-create]') : null;
    const directoryShareLinkCreateLabel = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-link-create-label]') : null;
    const directoryShareLinkCopyBtn = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-link-copy]') : null;
    const directoryShareLinkRevokeBtn = directoryShareForm ? directoryShareForm.querySelector('[data-directory-share-link-revoke]') : null;
    const directorySharePermissionFieldControls = directoryShareForm ? Array.from(directoryShareForm.querySelectorAll('.tasks-directory-share-permission-picker--field [data-directory-share-permission-toggle], .tasks-directory-share-permission-picker--field [data-directory-share-permission-option]')) : [];
    let directoryShareSearchValue = '';
    const contactAncoreLoginInput = contactCreateForm ? contactCreateForm.querySelector('[data-ancore-login-input]') : null;
    const contactAncoreLoginStatus = contactCreateForm ? contactCreateForm.querySelector('[data-ancore-login-status]') : null;
    const contactAncoreLoginUrl = contactCreateForm ? (contactCreateForm.dataset.ancoreLoginUrl || '') : '';
    const contactFirstNameInput = contactCreateForm ? contactCreateForm.querySelector('[name="first_name"]') : null;
    const companyNameInput = companyCreateForm ? companyCreateForm.querySelector('[name="name"]') : null;
    const projectSubmitBtn = document.getElementById('project-create-submit');
    const tagSubmitBtn = document.getElementById('tag-create-submit');
    const projectRenameSubmitBtn = document.getElementById('project-rename-submit');
    const sectionCreateSubmitBtn = document.getElementById('section-create-submit');
    const sectionRenameSubmitBtn = document.getElementById('section-rename-submit');
    const issueSubmitBtn = document.getElementById('issue-create-submit');
    const directoryShareSubmitBtn = document.getElementById('directory-share-submit');
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
            icon: 'star',
            items: ['rocket', 'star', 'circle-check', 'settings', 'lightbulb', 'pin', 'clipboard-list', 'folder', 'wrench', 'puzzle', 'target', 'chart-no-axes-combined', 'lock', 'flask-conical', 'monitor', 'smartphone', 'globe', 'cloud', 'sparkles', 'trophy', 'party-popper', 'map-pin', 'key-round', 'briefcase-business', 'calendar-days', 'paperclip', 'bell', 'message-square', 'megaphone', 'brain', 'compass', 'flag', 'shield', 'tag', 'package']
        },
        {
            label: 'Praca',
            icon: 'briefcase-business',
            items: ['briefcase-business', 'building-2', 'files', 'file-text', 'calendar', 'clock', 'tag', 'package', 'folder-open', 'receipt', 'mail', 'search', 'circle-check', 'triangle-alert', 'megaphone', 'handshake', 'users', 'brain', 'compass', 'notebook', 'contact', 'archive', 'send', 'inbox', 'id-card', 'landmark', 'phone', 'newspaper', 'message-square', 'chart-column', 'calculator', 'credit-card', 'scale', 'scroll-text', 'pen-line', 'paperclip']
        },
        {
            label: 'Technologia',
            icon: 'laptop',
            items: ['laptop', 'monitor', 'keyboard', 'mouse', 'smartphone', 'gamepad-2', 'database', 'disc', 'calculator', 'plug', 'battery', 'satellite-dish', 'bot', 'dna', 'microscope', 'flask-conical', 'magnet', 'cog', 'hammer', 'wrench', 'briefcase-business', 'printer', 'server', 'shield', 'wifi', 'lightbulb', 'lock', 'key-round', 'volume-2', 'camera', 'video', 'terminal', 'code', 'cpu', 'zap', 'cloud']
        },
        {
            label: 'Kreatywne',
            icon: 'palette',
            items: ['palette', 'paintbrush', 'brush', 'pencil', 'pen-tool', 'pen-line', 'ruler', 'scissors', 'theater', 'clapperboard', 'headphones', 'mic', 'music', 'piano', 'puzzle', 'wand-sparkles', 'camera', 'image', 'rainbow', 'sparkles', 'star', 'flame', 'lightbulb', 'film', 'ticket', 'shapes', 'sticker', 'notepad-text', 'bookmark', 'paperclip']
        },
        {
            label: 'Status',
            icon: 'zap',
            items: ['zap', 'flame', 'star', 'bell', 'circle', 'arrow-up', 'arrow-down', 'arrow-right', 'refresh-cw', 'hourglass', 'construction', 'shield', 'flag', 'party-popper', 'sparkles', 'circle-check', 'square-check', 'check', 'circle-x', 'triangle-alert', 'message-square', 'ban', 'plus', 'minus', 'asterisk', 'badge-alert', 'octagon-x', 'siren', 'flag-triangle-right']
        },
        {
            label: 'Zespół',
            icon: 'users',
            items: ['users', 'user', 'user-round', 'user-plus', 'user-check', 'user-cog', 'smile', 'handshake', 'thumbs-up', 'hand', 'heart', 'briefcase-business', 'graduation-cap', 'paintbrush', 'wrench', 'rocket', 'stethoscope', 'scale', 'badge-check', 'message-circle', 'messages-square', 'crown']
        },
        {
            label: 'Plan',
            icon: 'calendar-days',
            items: ['calendar-days', 'calendar', 'calendar-check', 'alarm-clock', 'timer', 'hourglass', 'clock', 'map-pin', 'compass', 'map', 'construction', 'traffic-cone', 'clipboard-list', 'notebook', 'pin', 'paperclip', 'bookmark', 'tag', 'target', 'flag', 'calculator', 'chart-column', 'chart-no-axes-combined', 'repeat', 'check', 'circle-check', 'triangle-alert']
        },
        {
            label: 'Biznes',
            icon: 'wallet',
            items: ['wallet', 'banknote', 'credit-card', 'receipt', 'landmark', 'building-2', 'store', 'factory', 'construction', 'truck', 'package', 'mail', 'phone', 'id-card', 'briefcase-business', 'shopping-cart', 'handshake', 'chart-column', 'chart-no-axes-combined', 'gem', 'scale', 'calculator', 'file-text', 'folder-open', 'clipboard-list', 'lock', 'key-round', 'megaphone', 'target', 'trophy']
        },
        {
            label: 'Miejsca',
            icon: 'globe',
            items: ['globe', 'map', 'building-2', 'school', 'landmark', 'hospital', 'factory', 'construction', 'train', 'plane', 'rocket', 'car', 'bike', 'ship', 'anchor', 'tent', 'mountain', 'map-pin', 'route', 'signpost', 'navigation', 'warehouse']
        },
        {
            label: 'Natura',
            icon: 'leaf',
            items: ['leaf', 'sprout', 'tree-pine', 'flower', 'sun', 'moon', 'cloud', 'cloud-rain', 'snowflake', 'droplet', 'waves', 'flame', 'gem', 'mountain', 'rainbow', 'wind', 'cloud-sun', 'cloud-lightning']
        },
        {
            label: 'Jedzenie',
            icon: 'pizza',
            items: ['pizza', 'sandwich', 'salad', 'soup', 'utensils', 'coffee', 'cup-soda', 'apple', 'carrot', 'cake', 'cookie', 'ice-cream-bowl', 'shopping-basket', 'package']
        },
        {
            label: 'Edukacja',
            icon: 'graduation-cap',
            items: ['graduation-cap', 'book-open', 'book', 'notebook', 'pencil', 'pen-line', 'calculator', 'ruler', 'microscope', 'flask-conical', 'dna', 'globe', 'map', 'brain', 'lightbulb', 'school', 'bookmark', 'medal', 'file-text', 'chart-column', 'search', 'compass', 'telescope', 'target', 'trophy', 'puzzle', 'timer']
        },
        {
            label: 'Sport',
            icon: 'medal',
            items: ['medal', 'trophy', 'dumbbell', 'bike', 'goal', 'flag', 'target', 'flame', 'zap', 'hand', 'timer', 'chart-column', 'mountain', 'waves', 'snowflake', 'ticket', 'megaphone', 'star']
        },
        {
            label: 'Zdrowie',
            icon: 'heart-pulse',
            items: ['heart-pulse', 'heart', 'stethoscope', 'pill', 'dna', 'microscope', 'hospital', 'ambulance', 'salad', 'apple', 'droplet', 'leaf', 'sun', 'bed', 'brain', 'dumbbell', 'alarm-clock', 'clipboard-list', 'sparkles', 'smile']
        },
        {
            label: 'Symbole',
            icon: 'shapes',
            items: ['heart', 'recycle', 'circle-check', 'square-check', 'check', 'x', 'plus', 'minus', 'asterisk', 'circle', 'square', 'triangle', 'diamond', 'badge-alert', 'octagon-x', 'ban', 'shield', 'sparkles', 'star']
        }
    ];
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
        rocket: ['rakieta', 'start', 'launch'],
        star: ['gwiazda', 'ulubione', 'star'],
        'circle-check': ['check', 'gotowe', 'zrobione', 'ok'],
        settings: ['ustawienia', 'trybik', 'settings'],
        lightbulb: ['pomysl', 'idea'],
        pin: ['pinezka', 'przypiete'],
        'clipboard-list': ['lista', 'clipboard'],
        folder: ['folder', 'projekt'],
        wrench: ['klucz', 'naprawa', 'narzedzie'],
        puzzle: ['puzzle', 'czesc'],
        target: ['cel', 'target'],
        'chart-no-axes-combined': ['wzrost', 'wykres'],
        lock: ['blokada', 'zamkniete'],
        monitor: ['monitor', 'komputer'],
        smartphone: ['telefon', 'mobile'],
        globe: ['internet', 'web', 'siec', 'swiat'],
        cloud: ['chmura', 'cloud'],
        'briefcase-business': ['praca', 'teczka', 'biuro'],
        laptop: ['laptop', 'komputer', 'kod'],
        palette: ['sztuka', 'design', 'kolor'],
        users: ['zespol', 'ludzie', 'team'],
        'calendar-days': ['kalendarz', 'plan', 'termin'],
        wallet: ['pieniadze', 'finanse'],
        leaf: ['natura', 'lisc', 'roslina'],
        pizza: ['pizza', 'jedzenie'],
        'graduation-cap': ['edukacja', 'nauka'],
        medal: ['medal', 'sport'],
        'heart-pulse': ['zdrowie', 'serce'],
        shapes: ['symbole', 'znaki'],
        calendar: ['data', 'kalendarz'],
        'alarm-clock': ['alarm', 'czas'],
        search: ['szukaj', 'lupa'],
        package: ['paczka', 'box'],
        'file-text': ['notatka', 'pisanie', 'dokument'],
        'building-2': ['firma', 'budynek'],
        phone: ['telefon', 'kontakt'],
        handshake: ['wspolpraca'],
        camera: ['aparat', 'foto'],
        flame: ['ogien', 'pilne'],
        bell: ['dzwonek', 'powiadomienie'],
        'circle-x': ['anuluj', 'blad'],
        'triangle-alert': ['uwaga', 'ostrzezenie'],
        house: ['dom', 'home'],
        heart: ['serce', 'milosc']
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
    let contactAncoreLoginTimer = null;
    let contactAncoreLoginRequestId = 0;

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

    function directoryShareCanManage() {
        return directoryShareForm?.dataset.shareCanManage !== 'false';
    }

    function setDirectoryShareManageState(canManage) {
        if (!directoryShareForm) return;
        directoryShareForm.dataset.shareCanManage = canManage ? 'true' : 'false';
        directoryShareForm.classList.toggle('is-readonly', !canManage);
        directorySharePersonInputs.forEach(input => {
            input.disabled = !canManage;
        });
        if (directoryShareSelectedInput) directoryShareSelectedInput.disabled = !canManage;
        if (directorySharePermissionInput) directorySharePermissionInput.disabled = !canManage;
        directorySharePermissionFieldControls.forEach(control => {
            control.disabled = !canManage;
        });
        updateDirectoryShareSubmitState();
    }

    function updateDirectoryShareSubmitState() {
        if (!directoryShareSubmitBtn) return;
        if (!directoryShareCanManage()) {
            directoryShareSubmitBtn.disabled = true;
            return;
        }
        const hasTypedQuery = directorySharePersonInputs.some(input => {
            const value = input.value.trim();
            return value.length > 0 && value !== '@';
        });
        directoryShareSubmitBtn.disabled = !hasTypedQuery && directoryShareSelectedValues().length === 0;
    }

    function updateDirectoryShareLinkState(linkUrl = '') {
        const hasLink = Boolean(linkUrl);
        if (directoryShareLinkInput) directoryShareLinkInput.value = linkUrl;
        if (directoryShareLinkCreateLabel) directoryShareLinkCreateLabel.textContent = hasLink ? 'Odśwież link' : 'Utwórz link';
        if (directoryShareLinkCreateBtn) directoryShareLinkCreateBtn.disabled = !directoryShareCanManage();
        if (directoryShareLinkCopyBtn) directoryShareLinkCopyBtn.disabled = !directoryShareCanManage() || !hasLink;
        if (directoryShareLinkRevokeBtn) directoryShareLinkRevokeBtn.disabled = !directoryShareCanManage() || !hasLink;
    }

    function directoryShareObjectPayload() {
        const objectType = directoryShareObjectTypeInput?.value || '';
        const objectId = directoryShareObjectIdInput?.value || '';
        if (!objectType || !objectId) return null;

        const payload = new FormData();
        payload.append('object_type', objectType);
        payload.append('object_id', objectId);
        payload.append('permission', directorySharePermissionInput?.value || 'view');
        return payload;
    }

    function setDirectoryShareLinkButtonsLoading(isLoading) {
        [directoryShareLinkCreateBtn, directoryShareLinkCopyBtn, directoryShareLinkRevokeBtn].forEach(button => {
            if (!button) return;
            if (isLoading) {
                button.disabled = true;
                button.setAttribute('aria-busy', 'true');
            } else {
                button.removeAttribute('aria-busy');
            }
        });
        if (!isLoading) updateDirectoryShareLinkState(directoryShareLinkInput?.value || '');
    }

    function directoryShareSearchTerms() {
        const query = normalizePickerSearch(directoryShareSearchValue);
        return query ? [query] : [];
    }

    function directoryShareTokensFromInput(value) {
        return (value || '')
            .split(':')
            .map(token => token.trim())
            .filter(token => token !== '@')
            .filter(Boolean);
    }

    function normalizeDirectoryShareValue(value) {
        value = (value || '').trim().toLowerCase();
        if (!value) return '';
        return value.startsWith('@') ? value : `@${value}`;
    }

    function directoryShareActiveInputQuery(value) {
        const parts = (value || '').split(':');
        return (parts[parts.length - 1] || '').trim();
    }

    function directoryShareCommittedTokensFromInput(value) {
        const tokens = directoryShareTokensFromInput(value);
        const activeQuery = directoryShareActiveInputQuery(value);
        if (!tokens.length || !activeQuery) return tokens;
        if (/:\s*$/.test(value || '')) return tokens;
        return tokens.slice(0, -1);
    }

    function directoryShareSelectedText(values) {
        return values.join(': ');
    }

    function directoryShareSelectedValues() {
        return (directoryShareSelectedInput?.value || '')
            .split('\n')
            .map(value => value.trim())
            .filter(Boolean);
    }

    function setDirectoryShareSelectedValues(values, syncVisibleInput = false) {
        if (!directoryShareSelectedInput) return;
        const selectedValues = [];
        const seenValues = new Set();
        values.forEach(value => {
            value = (value || '').trim();
            const valueKey = normalizeDirectoryShareValue(value);
            if (!value || seenValues.has(valueKey)) return;
            seenValues.add(valueKey);
            selectedValues.push(valueKey);
        });
        directoryShareSelectedInput.value = selectedValues.join('\n');
        if (syncVisibleInput && directoryShareMemberInput) {
            directoryShareMemberInput.value = directoryShareSelectedText(selectedValues);
        }
    }

    function directoryShareSelectedSet() {
        return new Set(
            directoryShareSelectedValues()
                .map(normalizeDirectoryShareValue)
                .filter(Boolean)
        );
    }

    function setDirectorySharePickOptionSelected(option, shouldSelect) {
        const value = option?.dataset.shareValue || '';
        if (!value) return;
        const valueKey = normalizeDirectoryShareValue(value);
        const selectedValues = directoryShareSelectedValues();
        const isSelected = selectedValues.some(selectedValue => normalizeDirectoryShareValue(selectedValue) === valueKey);
        setDirectoryShareSelectedValues(
            shouldSelect
                ? (isSelected ? selectedValues : [...selectedValues, value])
                : selectedValues.filter(selectedValue => normalizeDirectoryShareValue(selectedValue) !== valueKey),
            true
        );
        updateDirectoryShareSubmitState();
        syncDirectoryShareResults();
        directoryShareMemberInput?.focus();
    }

    function toggleDirectorySharePickOption(option) {
        const value = option?.dataset.shareValue || '';
        if (!value) return;
        const valueKey = normalizeDirectoryShareValue(value);
        const isSelected = directoryShareSelectedSet().has(valueKey);
        setDirectorySharePickOptionSelected(option, !isSelected);
    }

    function toggleDirectorySharePickOptionFromCheckbox(option, checkbox) {
        if (!checkbox) return;
        setDirectorySharePickOptionSelected(option, checkbox.checked);
    }

    function hasIncompleteDirectoryShareSearch() {
        return normalizePickerSearch(directoryShareSearchValue) === '@';
    }

    function syncDirectoryShareSelectedValuesFromInput(input) {
        const value = input?.value || '';
        directoryShareSearchValue = directoryShareActiveInputQuery(value);
        setDirectoryShareSelectedValues(directoryShareCommittedTokensFromInput(value));
    }

    function setDirectoryShareContactsOpen(isOpen) {
        if (directoryShareResults) directoryShareResults.hidden = !isOpen;
    }

    function syncDirectoryShareResults() {
        const terms = directoryShareSearchTerms();
        const hasIncompleteSearch = hasIncompleteDirectoryShareSearch();
        const selectedValues = directoryShareSelectedSet();
        let visibleContactsCount = 0;

        directoryShareContactOptions.forEach(option => {
            const text = normalizePickerSearch(option.dataset.shareSearch || option.textContent);
            const isSelected = selectedValues.has(normalizeDirectoryShareValue(option.dataset.shareValue || ''));
            const isVisible = isSelected || (!hasIncompleteSearch && (!terms.length || terms.every(term => text.includes(term))));
            option.hidden = !isVisible;
            option.classList.toggle('is-active', isSelected);
            option.setAttribute('aria-selected', isSelected ? 'true' : 'false');
            const checkbox = option.querySelector('[data-directory-share-check]');
            if (checkbox) checkbox.checked = isSelected;
            if (isVisible) visibleContactsCount += 1;
        });

        const hasContacts = directoryShareContactOptions.length > 0;
        const emptyMessage = (terms.length || hasIncompleteSearch) && hasContacts
            ? 'Brak użytkowników dla tego wyszukiwania.'
            : 'Brak użytkowników.';

        [directoryShareContactsEmpty, directoryShareResultsEmpty].forEach(empty => {
            if (!empty) return;
            empty.textContent = emptyMessage;
            empty.hidden = hasContacts && visibleContactsCount > 0;
        });
    }

    function renderDirectoryShareMembers(templateId) {
        if (!directoryShareSharedList) return;
        directoryShareSharedList.replaceChildren();

        const template = templateId ? document.getElementById(templateId) : null;
        if (template) {
            directoryShareSharedList.append(template.content.cloneNode(true));
        }

        const rows = Array.from(directoryShareSharedList.querySelectorAll('[data-directory-share-shared-row]'));
        if (directoryShareSharedEmpty) directoryShareSharedEmpty.hidden = rows.length > 0;
        if (directoryShareSharedCount) directoryShareSharedCount.textContent = String(rows.length);
        initDirectorySharePermissionPickers(directoryShareSharedList);

        rows.forEach(row => {
            row.querySelector('[data-directory-share-remove]')?.addEventListener('click', function() {
                if (directoryShareActionInput) directoryShareActionInput.value = this.dataset.shareAction || '';
                if (directoryShareProjectInput) directoryShareProjectInput.value = this.dataset.shareProjectId || '';
                if (directoryShareSectionInput) directoryShareSectionInput.value = this.dataset.shareSectionId || '';
                if (directoryShareTaskInput) directoryShareTaskInput.value = this.dataset.shareTaskId || '';
                if (directoryShareMemberIdInput) directoryShareMemberIdInput.value = this.dataset.shareMemberId || '';
                directorySharePersonInputs.forEach(input => { input.value = ''; });
                directoryShareForm.requestSubmit ? directoryShareForm.requestSubmit() : directoryShareForm.submit();
            });
        });

        if (window.AncoreIcons?.render) {
            window.AncoreIcons.render(directoryShareSharedList);
        } else if (window.lucide?.createIcons) {
            window.lucide.createIcons();
        }
    }

    function syncDirectoryShareTriggerLink(linkUrl, permission = '') {
        const objectType = directoryShareObjectTypeInput?.value || '';
        const objectId = directoryShareObjectIdInput?.value || '';
        if (!objectType || !objectId) return;

        const escapeSelectorValue = window.CSS?.escape || (value => String(value).replace(/"/g, '\\"'));
        document.querySelectorAll(`[data-share-object-kind="${escapeSelectorValue(objectType)}"][data-share-object-id="${escapeSelectorValue(objectId)}"]`).forEach(button => {
            button.dataset.shareLinkUrl = linkUrl || '';
            if (permission) button.dataset.shareLinkPermission = permission;
        });
    }

    async function postDirectoryShareLink(endpoint) {
        const payload = directoryShareObjectPayload();
        if (!endpoint || !payload) throw new Error('Nie wybrano elementu do udostępnienia.');

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {
                'X-CSRFToken': window.getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: payload
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'success') {
            throw new Error(data.message || 'Nie udało się zaktualizować linku.');
        }
        return data;
    }

    async function createDirectoryShareLink() {
        if (!directoryShareForm) return;
        setDirectoryShareLinkButtonsLoading(true);
        try {
            const data = await postDirectoryShareLink(directoryShareForm.dataset.shareLinkCreateUrl || '');
            updateDirectoryShareLinkState(data.url || '');
            syncDirectoryShareTriggerLink(data.url || '', data.permission || directorySharePermissionInput?.value || 'view');
            showMessage('Link udostępniania jest gotowy.', 'success');
        } catch (error) {
            showMessage(error.message || 'Nie udało się utworzyć linku.', 'error');
        } finally {
            setDirectoryShareLinkButtonsLoading(false);
        }
    }

    async function revokeDirectoryShareLink() {
        if (!directoryShareForm) return;
        setDirectoryShareLinkButtonsLoading(true);
        try {
            await postDirectoryShareLink(directoryShareForm.dataset.shareLinkRevokeUrl || '');
            updateDirectoryShareLinkState('');
            syncDirectoryShareTriggerLink('', directorySharePermissionInput?.value || 'view');
            showMessage('Link udostępniania został wyłączony.', 'success');
        } catch (error) {
            showMessage(error.message || 'Nie udało się wyłączyć linku.', 'error');
        } finally {
            setDirectoryShareLinkButtonsLoading(false);
        }
    }

    async function copyDirectoryShareLink() {
        const linkUrl = directoryShareLinkInput?.value || '';
        if (!linkUrl) return;

        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(linkUrl);
            } else {
                directoryShareLinkInput.focus();
                directoryShareLinkInput.select();
                document.execCommand('copy');
            }
            showMessage('Link skopiowany.', 'success');
        } catch (error) {
            showMessage('Nie udało się skopiować linku.', 'error');
        }
    }

    function updateProjectRenameSubmitState() {
        if (!projectRenameSubmitBtn || !projectRenameNameInput) return;
        projectRenameSubmitBtn.disabled = projectRenameNameInput.value.trim().length === 0;
    }

    function updateSectionCreateSubmitState() {
        if (!sectionCreateSubmitBtn || !sectionCreateTitleInput) return;
        const hasTitle = sectionCreateTitleInput.value.trim().length > 0;
        const hasProject = !sectionCreateProjectSelect || sectionCreateProjectSelect.value.trim().length > 0;
        sectionCreateSubmitBtn.disabled = !hasTitle || !hasProject;
    }

    function updateSectionRenameSubmitState() {
        if (!sectionRenameSubmitBtn || !sectionRenameTitleInput) return;
        sectionRenameSubmitBtn.disabled = sectionRenameTitleInput.value.trim().length === 0;
    }

    function setContactAncoreLoginStatus(message, state = '') {
        if (!contactAncoreLoginStatus) return;
        contactAncoreLoginStatus.textContent = message;
        contactAncoreLoginStatus.dataset.state = state;
    }

    function setContactFieldValue(name, value) {
        const field = contactCreateForm ? contactCreateForm.querySelector(`[name="${name}"]`) : null;
        if (!field) return;
        field.value = value || '';
        field.dispatchEvent(new Event('input', { bubbles: true }));
        field.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function fillContactFromAncoreUser(user) {
        if (!user) return;
        setContactFieldValue('first_name', user.first_name);
        setContactFieldValue('middle_name', user.middle_name);
        setContactFieldValue('last_name', user.last_name);
        setContactFieldValue('email', user.email);
        setContactFieldValue('phone', user.phone);
        setContactFieldValue('role', user.role);
        setContactFieldValue('source', user.source);
    }

    async function lookupContactAncoreLogin() {
        if (!contactAncoreLoginInput || !contactAncoreLoginUrl) return;
        const login = contactAncoreLoginInput.value.trim();
        contactAncoreLoginRequestId += 1;
        const requestId = contactAncoreLoginRequestId;

        if (!login) {
            setContactAncoreLoginStatus('');
            return;
        }

        if (login.length < 2) {
            setContactAncoreLoginStatus('Wpisz ID Ancore.', 'muted');
            return;
        }

        setContactAncoreLoginStatus('Szukam...', 'loading');

        try {
            const url = new URL(contactAncoreLoginUrl, window.location.origin);
            url.searchParams.set('login', login);
            const response = await fetch(url.toString(), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });
            if (requestId !== contactAncoreLoginRequestId) return;
            if (!response.ok) throw new Error('Lookup failed');
            const payload = await response.json();
            if (payload.found && payload.user) {
                fillContactFromAncoreUser(payload.user);
                if (contactAncoreLoginInput.value !== payload.user.username) {
                    contactAncoreLoginInput.value = payload.user.username;
                }
                setContactAncoreLoginStatus('Dane uzupełnione.', 'success');
            } else {
                setContactAncoreLoginStatus('Nie znaleziono użytkownika.', 'error');
            }
        } catch (error) {
            if (requestId !== contactAncoreLoginRequestId) return;
            setContactAncoreLoginStatus('Nie udało się sprawdzić ID Ancore.', 'error');
        }
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

    function closeProjectFilterMenus(exceptMenu = null) {
        projectFilterMenus.forEach(menu => {
            if (menu === exceptMenu) return;
            menu.classList.remove('is-open');
            menu.querySelector('[data-project-filter-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function closeProjectSortMenu() {
        projectSortMenu?.classList.remove('is-open');
        projectSortToggle?.setAttribute('aria-expanded', 'false');
    }

    function closeDirectoryMembersMenus(exceptMenu = null) {
        directoryMembersMenus.forEach(menu => {
            if (menu === exceptMenu) return;
            menu.classList.remove('is-open');
            menu.querySelector('[data-directory-members-toggle]')?.setAttribute('aria-expanded', 'false');
            menu.querySelectorAll('[data-directory-member-actions][open]').forEach(details => {
                details.removeAttribute('open');
            });
        });
    }

    function filterDirectoryMembers(menu) {
        if (!menu) return;
        const input = menu.querySelector('[data-directory-members-search]');
        const rows = Array.from(menu.querySelectorAll('[data-directory-member-row]'));
        const empty = menu.querySelector('[data-directory-members-no-results]');
        const query = normalizePickerSearch(input?.value || '');
        let visibleCount = 0;

        rows.forEach(row => {
            const text = normalizePickerSearch(row.dataset.directoryMemberSearch || row.textContent);
            const isVisible = !query || text.includes(query);
            row.hidden = !isVisible;
            if (isVisible) visibleCount += 1;
        });

        if (empty) {
            empty.hidden = !query || visibleCount > 0;
        }
    }

    function closeInlineSelectDropdowns(exceptDropdown = null) {
        document.querySelectorAll('[data-inline-select-dropdown]').forEach(dropdown => {
            if (dropdown === exceptDropdown) return;
            dropdown.classList.remove('is-open');
            dropdown.querySelector('[data-inline-select-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function closeProjectPageSizeDropdown() {
        projectPageSizeDropdown?.classList.remove('is-open');
        projectPageSizeToggle?.setAttribute('aria-expanded', 'false');
    }

    function closeTaskStatusPageSizeDropdowns(exceptDropdown = null) {
        document.querySelectorAll('[data-task-status-page-size-dropdown]').forEach(dropdown => {
            if (dropdown === exceptDropdown) return;
            dropdown.classList.remove('is-open');
            dropdown.querySelector('[data-task-status-page-size-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function closeCompanySelectDropdowns(exceptDropdown = null) {
        document.querySelectorAll('[data-company-select-dropdown]').forEach(dropdown => {
            if (dropdown === exceptDropdown) return;
            dropdown.classList.remove('is-open');
            dropdown.querySelector('[data-company-select-toggle]')?.setAttribute('aria-expanded', 'false');
            getCompanySelectMenu(dropdown)?.classList.remove('is-open');
        });
    }

    function closeResponsibleSelectDropdowns(exceptDropdown = null) {
        document.querySelectorAll('[data-responsible-select-dropdown]').forEach(dropdown => {
            if (dropdown === exceptDropdown) return;
            dropdown.classList.remove('is-open');
            dropdown.querySelector('[data-responsible-select-toggle]')?.setAttribute('aria-expanded', 'false');
            getResponsibleSelectMenu(dropdown)?.classList.remove('is-open');
        });
    }

    function getCompanySelectMenu(dropdown) {
        const menuId = dropdown?.dataset.companySelectDropdown;
        if (menuId) {
            const escapedMenuId = window.CSS?.escape ? CSS.escape(menuId) : menuId.replace(/"/g, '\\"');
            return document.querySelector(`[data-company-select-menu="${escapedMenuId}"]`);
        }
        return dropdown?.querySelector('.tasks-company-select__menu');
    }

    function getResponsibleSelectMenu(dropdown) {
        const menuId = dropdown?.dataset.responsibleSelectDropdown;
        if (menuId) {
            const escapedMenuId = window.CSS?.escape ? CSS.escape(menuId) : menuId.replace(/"/g, '\\"');
            return document.querySelector(`[data-responsible-select-menu="${escapedMenuId}"]`);
        }
        return dropdown?.querySelector('.tasks-responsible-select__menu');
    }

    function syncCompanySelectDropdown(dropdown) {
        const select = dropdown?.closest('.tasks-company-select-wrap')?.querySelector('select');
        if (!select) return;

        const currentValue = select.value || '';
        const menu = getCompanySelectMenu(dropdown);
        const activeButton = Array.from(menu?.querySelectorAll('[data-company-select-value]') || []).find(button => button.dataset.companySelectValue === currentValue);
        const label = dropdown.querySelector('[data-company-select-label]');
        const currentIcon = dropdown.querySelector('[data-company-select-current-icon]');

        menu?.querySelectorAll('[data-company-select-value]').forEach(button => {
            button.classList.toggle('is-active', button.dataset.companySelectValue === currentValue);
        });

        if (label && activeButton) {
            label.textContent = activeButton.dataset.companySelectName || activeButton.textContent.trim();
        }

        if (currentIcon && activeButton) {
            const activeIcon = activeButton.querySelector('.tasks-company-select__avatar, .tasks-company-select__empty-icon');
            currentIcon.replaceChildren();
            if (activeIcon) {
                currentIcon.appendChild(activeIcon.cloneNode(true));
            }
            window.AncoreIcons?.render(currentIcon);
        }
    }

    function filterCompanySelectOptions(dropdown) {
        const menu = getCompanySelectMenu(dropdown);
        const input = menu?.querySelector('[data-company-select-search]');
        const empty = menu?.querySelector('[data-company-select-empty]');
        const table = menu?.querySelector('.tasks-company-select__table');
        const query = normalizePickerSearch(input?.value || '');
        const select = dropdown?.closest('.tasks-company-select-wrap')?.querySelector('select');
        const currentValue = select?.value || '';
        let visibleCount = 0;

        menu?.querySelectorAll('[data-company-select-value]').forEach(button => {
            const text = normalizePickerSearch(button.dataset.companySelectSearchText || button.textContent);
            const isSelectedCompany = !query && currentValue && button.dataset.companySelectValue === currentValue;
            const isVisible = isSelectedCompany || (Boolean(query) && text.includes(query));
            button.hidden = !isVisible;
            if (isVisible) visibleCount += 1;
        });

        if (table) {
            table.hidden = visibleCount === 0;
        }

        if (empty) {
            empty.hidden = !query || visibleCount > 0;
        }
    }

    function syncCompanySelectForSelect(select) {
        const dropdown = select?.closest('.tasks-company-select-wrap')?.querySelector('[data-company-select-dropdown]');
        syncCompanySelectDropdown(dropdown);
    }

    function setResponsibleSelectStatus(dropdown, message = '', state = '') {
        const status = getResponsibleSelectMenu(dropdown)?.querySelector('[data-responsible-select-status]');
        if (!status) return;
        status.textContent = message;
        if (state) {
            status.dataset.state = state;
        } else {
            status.removeAttribute('data-state');
        }
    }

    function ensureResponsibleSelectOption(select, user) {
        if (!select || !user?.id) return null;
        const value = String(user.id);
        let option = Array.from(select.options).find(item => item.value === value);
        if (!option) {
            option = new Option(user.label || user.username || user.email || 'Osoba', value);
            select.appendChild(option);
        }
        option.textContent = user.label || user.username || user.email || option.textContent;
        return option;
    }

    function ensureResponsibleSelectButton(dropdown, user) {
        if (!dropdown || !user?.id) return null;
        const menu = getResponsibleSelectMenu(dropdown);
        const value = String(user.id);
        let button = Array.from(menu?.querySelectorAll('[data-responsible-select-value]') || []).find(item => item.dataset.responsibleSelectValue === value);
        if (!button) {
            button = document.createElement('button');
            button.type = 'button';
            button.setAttribute('role', 'menuitemradio');
            button.setAttribute('aria-checked', 'false');
            button.dataset.responsibleSelectValue = value;
            const avatar = document.createElement('span');
            avatar.className = 'profile-avatar tasks-responsible-select__avatar';
            avatar.setAttribute('aria-hidden', 'true');
            const person = document.createElement('span');
            person.className = 'tasks-responsible-select__person';
            const identity = document.createElement('span');
            identity.className = 'tasks-responsible-select__identity';
            const label = document.createElement('span');
            label.className = 'tasks-responsible-select__name';
            const username = document.createElement('span');
            username.className = 'tasks-responsible-select__username';
            identity.append(label, username);
            person.append(avatar, identity);
            const check = document.createElement('span');
            check.className = 'tasks-responsible-select__check';
            check.setAttribute('aria-hidden', 'true');
            button.append(person, check);
            const table = menu?.querySelector('.tasks-responsible-select__table');
            table?.appendChild(button);
        }

        const labelText = user.label || user.username || user.email || 'Osoba';
        const usernameText = user.username || '';
        button.dataset.responsibleSelectName = labelText;
        button.dataset.responsibleSelectUsername = usernameText;
        button.dataset.responsibleSelectSearchText = `${labelText} ${usernameText} ${user.email || ''}`.toLowerCase();

        const avatar = button.querySelector('.tasks-responsible-select__avatar');
        if (avatar) {
            avatar.classList.toggle('has-photo', Boolean(user.avatar?.photo_url));
            avatar.classList.add(user.avatar?.color_class || '');
            if (user.avatar?.color_style) avatar.setAttribute('style', user.avatar.color_style);
            avatar.replaceChildren();
            if (user.avatar?.photo_url) {
                const image = document.createElement('img');
                image.src = user.avatar.photo_url;
                image.alt = '';
                avatar.appendChild(image);
            } else {
                avatar.textContent = user.avatar?.initials || labelText.trim().charAt(0).toUpperCase() || 'O';
            }
        }

        const name = button.querySelector('.tasks-responsible-select__name');
        const username = button.querySelector('.tasks-responsible-select__username');
        if (name) name.textContent = labelText;
        if (username) username.textContent = usernameText;
        return button;
    }

    function setResponsibleSelectDraft(dropdown, value) {
        if (!dropdown) return;
        const menu = getResponsibleSelectMenu(dropdown);
        const draftValue = value || '';
        dropdown.dataset.responsibleDraftValue = draftValue;
        menu?.querySelectorAll('[data-responsible-select-value]').forEach(button => {
            const isActive = button.dataset.responsibleSelectValue === draftValue;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-checked', String(isActive));
        });
    }

    function syncResponsibleSelectDropdown(dropdown) {
        const select = dropdown?.closest('.tasks-responsible-select-wrap')?.querySelector('select');
        if (!select) return;

        const currentValue = select.value || '';
        const menu = getResponsibleSelectMenu(dropdown);
        const hasCurrentButton = Array.from(menu?.querySelectorAll('[data-responsible-select-value]') || []).some(button => button.dataset.responsibleSelectValue === currentValue);
        if (currentValue && !hasCurrentButton) {
            const selectedOption = Array.from(select.options).find(option => option.value === currentValue);
            if (selectedOption) {
                ensureResponsibleSelectButton(dropdown, {
                    id: currentValue,
                    label: selectedOption.textContent.trim()
                });
            }
        }
        const activeButton = Array.from(menu?.querySelectorAll('[data-responsible-select-value]') || []).find(button => button.dataset.responsibleSelectValue === currentValue);
        const label = dropdown.querySelector('[data-responsible-select-label]');
        const currentIcon = dropdown.querySelector('[data-responsible-select-current-icon]');

        setResponsibleSelectDraft(dropdown, currentValue);

        if (label && activeButton) {
            label.textContent = activeButton.dataset.responsibleSelectName || activeButton.textContent.trim();
        }

        if (currentIcon && activeButton) {
            const activeIcon = activeButton.querySelector('.tasks-responsible-select__avatar, .tasks-responsible-select__empty-icon');
            currentIcon.replaceChildren();
            if (activeIcon) {
                currentIcon.appendChild(activeIcon.cloneNode(true));
            }
            window.AncoreIcons?.render(currentIcon);
        }
    }

    function filterResponsibleSelectOptions(dropdown) {
        const menu = getResponsibleSelectMenu(dropdown);
        const input = menu?.querySelector('[data-responsible-select-search]');
        const table = menu?.querySelector('.tasks-responsible-select__table');
        const query = normalizePickerSearch(input?.value || '');
        const select = dropdown?.closest('.tasks-responsible-select-wrap')?.querySelector('select');
        const currentValue = select?.value || '';
        let visibleCount = 0;

        menu?.querySelectorAll('[data-responsible-select-value]').forEach(button => {
            const text = normalizePickerSearch(button.dataset.responsibleSelectSearchText || button.textContent);
            const isSelectedPerson = !query && currentValue && button.dataset.responsibleSelectValue === currentValue;
            const isVisible = isSelectedPerson || (Boolean(query) && text.includes(query));
            button.hidden = !isVisible;
            if (isVisible) visibleCount += 1;
        });

        if (table) {
            table.hidden = visibleCount === 0;
        }
    }

    function syncResponsibleSelectForSelect(select) {
        const dropdown = select?.closest('.tasks-responsible-select-wrap')?.querySelector('[data-responsible-select-dropdown]');
        syncResponsibleSelectDropdown(dropdown);
    }

    const DIRECTORY_SHARE_PERMISSION_META = {
        view: { label: 'Może przeglądać', icon: 'eye' },
        edit: { label: 'Może przeglądać i edytować', icon: 'pen-line' }
    };

    function normalizeDirectorySharePermission(value) {
        return value === 'edit' ? 'edit' : 'view';
    }

    function renderDirectorySharePermissionIcon(picker, iconName) {
        const currentIcon = picker.querySelector('[data-directory-share-permission-current-icon]');
        if (!currentIcon || currentIcon.getAttribute('data-lucide') === iconName) return;

        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', iconName);
        icon.setAttribute('aria-hidden', 'true');
        icon.setAttribute('data-directory-share-permission-current-icon', '');
        currentIcon.replaceWith(icon);

        if (window.AncoreIcons?.render) {
            window.AncoreIcons.render(picker);
        } else if (window.lucide?.createIcons) {
            window.lucide.createIcons();
        }
    }

    function updateDirectorySharePermissionPicker(picker, value) {
        if (!picker) return;
        const permission = normalizeDirectorySharePermission(value || picker.dataset.permissionValue);
        const meta = DIRECTORY_SHARE_PERMISSION_META[permission];
        picker.dataset.permissionValue = permission;
        picker.classList.toggle('is-view', permission === 'view');
        picker.classList.toggle('is-edit', permission === 'edit');

        const hiddenInput = picker.querySelector('[data-directory-share-permission-hidden]');
        if (hiddenInput) hiddenInput.value = permission;

        const currentLabel = picker.querySelector('[data-directory-share-permission-current-label]');
        if (currentLabel) currentLabel.textContent = meta.label;
        renderDirectorySharePermissionIcon(picker, meta.icon);

        picker.querySelectorAll('[data-directory-share-permission-option]').forEach(option => {
            const isActive = normalizeDirectorySharePermission(option.dataset.permissionValue) === permission;
            option.classList.toggle('is-active', isActive);
            option.setAttribute('aria-selected', isActive ? 'true' : 'false');
        });
    }

    function syncDirectorySharePermissionPickers(root = document) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('[data-directory-share-permission-picker]').forEach(picker => {
            const hiddenInput = picker.querySelector('[data-directory-share-permission-hidden]');
            updateDirectorySharePermissionPicker(picker, hiddenInput?.value || picker.dataset.permissionValue);
        });
    }

    function resetDirectorySharePermissionMenuPosition(menu) {
        if (!menu) return;
        menu.classList.remove('is-floating');
        ['position', 'top', 'right', 'bottom', 'left', 'width', 'minWidth', 'maxWidth', 'zIndex'].forEach(property => {
            menu.style[property] = '';
        });
    }

    function positionDirectorySharePermissionMenu(picker) {
        const menu = picker?.querySelector('[data-directory-share-permission-menu]');
        const toggle = picker?.querySelector('[data-directory-share-permission-toggle]');
        if (!menu || !toggle || menu.hidden) return;

        const toggleRect = toggle.getBoundingClientRect();
        const viewportWidth = window.innerWidth || document.documentElement.clientWidth;
        const viewportHeight = window.innerHeight || document.documentElement.clientHeight;
        const viewportGap = 8;
        const menuGap = 6;
        const desiredWidth = picker.classList.contains('tasks-directory-share-permission-picker--row') ? 260 : Math.max(toggleRect.width, 240);
        const menuWidth = Math.max(160, Math.min(desiredWidth, viewportWidth - (viewportGap * 2)));

        menu.classList.add('is-floating');
        menu.style.position = 'fixed';
        menu.style.width = `${menuWidth}px`;
        menu.style.minWidth = '0';
        menu.style.maxWidth = `${menuWidth}px`;
        menu.style.right = 'auto';
        menu.style.bottom = 'auto';
        menu.style.zIndex = '2400';

        const menuHeight = menu.offsetHeight;
        let left = toggleRect.right - menuWidth;
        left = Math.max(viewportGap, Math.min(left, viewportWidth - menuWidth - viewportGap));

        let top = toggleRect.bottom + menuGap;
        if (top + menuHeight > viewportHeight - viewportGap) {
            top = toggleRect.top - menuHeight - menuGap;
        }
        top = Math.max(viewportGap, Math.min(top, viewportHeight - menuHeight - viewportGap));

        menu.style.left = `${left}px`;
        menu.style.top = `${top}px`;
    }

    function repositionOpenDirectorySharePermissionMenus() {
        document.querySelectorAll('[data-directory-share-permission-picker].is-open').forEach(positionDirectorySharePermissionMenu);
    }

    function closeDirectorySharePermissionPickers(exceptPicker = null, restoreFocus = false) {
        document.querySelectorAll('[data-directory-share-permission-picker].is-open').forEach(picker => {
            if (picker === exceptPicker) return;
            picker.classList.remove('is-open');
            picker.querySelector('[data-directory-share-permission-toggle]')?.setAttribute('aria-expanded', 'false');
            const menu = picker.querySelector('[data-directory-share-permission-menu]');
            if (menu) {
                menu.hidden = true;
                resetDirectorySharePermissionMenuPosition(menu);
            }
            if (restoreFocus) picker.querySelector('[data-directory-share-permission-toggle]')?.focus();
        });
    }

    function openDirectorySharePermissionPicker(picker, focusSelected = false) {
        if (!picker) return;
        closeCreateMenu();
        closeProjectActionMenus();
        closeSectionActionMenu();
        closeStatusFilterMenu();
        closePriorityFilterMenu();
        closeIssuePickers();
        closeInlineSelectDropdowns();
        closeDirectorySharePermissionPickers(picker);

        picker.classList.add('is-open');
        picker.querySelector('[data-directory-share-permission-toggle]')?.setAttribute('aria-expanded', 'true');
        const menu = picker.querySelector('[data-directory-share-permission-menu]');
        if (menu) {
            menu.hidden = false;
            positionDirectorySharePermissionMenu(picker);
        }
        if (focusSelected) {
            (picker.querySelector('[data-directory-share-permission-option].is-active') || picker.querySelector('[data-directory-share-permission-option]'))?.focus();
        }
    }

    function directorySharePermissionPayload(option, permission) {
        const payload = new FormData(directoryShareForm);
        payload.set('action', option.dataset.shareAction || '');
        payload.set('project_id', option.dataset.shareProjectId || '');
        payload.set('section_id', option.dataset.shareSectionId || '');
        payload.set('task_id', option.dataset.shareTaskId || '');
        payload.set('member_id', option.dataset.shareMemberId || '');
        payload.set('permission', permission);
        directorySharePersonInputs.forEach(input => {
            if (input.name) payload.set(input.name, '');
        });
        payload.set('member_queries', '');
        return payload;
    }

    function setDirectorySharePermissionPickerLoading(picker, isLoading) {
        if (!picker) return;
        picker.classList.toggle('is-saving', isLoading);
        if (isLoading) {
            picker.setAttribute('aria-busy', 'true');
        } else {
            picker.removeAttribute('aria-busy');
        }
        picker.querySelectorAll('[data-directory-share-permission-toggle], [data-directory-share-permission-option]').forEach(control => {
            control.disabled = isLoading;
        });
    }

    async function submitDirectorySharePermissionOption(option, permission, previousPermission, picker) {
        if (!directoryShareForm || !option.hasAttribute('data-directory-share-permission-submit')) return;

        const endpoint = directoryShareForm.getAttribute('action') || window.location.href;
        setDirectorySharePermissionPickerLoading(picker, true);
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: directorySharePermissionPayload(option, permission)
            });
            const contentType = response.headers.get('content-type') || '';
            const data = contentType.includes('application/json') ? await response.json() : {};
            if (!response.ok || data.status !== 'success') {
                throw new Error(data.message || 'Nie udało się zmienić poziomu dostępu.');
            }
            updateDirectorySharePermissionPicker(picker, data.permission || permission);
            showMessage(data.message || 'Zmieniono poziom dostępu.', 'success');
        } catch (error) {
            updateDirectorySharePermissionPicker(picker, previousPermission);
            showMessage(error.message || 'Nie udało się zmienić poziomu dostępu.', 'error');
        } finally {
            setDirectorySharePermissionPickerLoading(picker, false);
        }
    }

    function selectDirectorySharePermissionOption(option) {
        const picker = option?.closest('[data-directory-share-permission-picker]');
        if (!picker) return;
        const previousPermission = normalizeDirectorySharePermission(picker.dataset.permissionValue);
        const permission = normalizeDirectorySharePermission(option.dataset.permissionValue);
        updateDirectorySharePermissionPicker(picker, permission);
        closeDirectorySharePermissionPickers();
        if (permission !== previousPermission) {
            submitDirectorySharePermissionOption(option, permission, previousPermission, picker);
        }
    }

    function focusDirectorySharePermissionOption(option, direction) {
        const picker = option.closest('[data-directory-share-permission-picker]');
        const options = Array.from(picker.querySelectorAll('[data-directory-share-permission-option]'));
        if (!options.length) return;
        const currentIndex = Math.max(0, options.indexOf(option));
        const nextIndex = (currentIndex + direction + options.length) % options.length;
        options[nextIndex].focus();
    }

    function initDirectorySharePermissionPickers(root = document) {
        const scope = root && root.querySelectorAll ? root : document;
        scope.querySelectorAll('[data-directory-share-permission-picker]').forEach(picker => {
            if (picker.dataset.permissionPickerReady === 'true') {
                updateDirectorySharePermissionPicker(picker, picker.dataset.permissionValue);
                return;
            }
            picker.dataset.permissionPickerReady = 'true';

            updateDirectorySharePermissionPicker(picker, picker.dataset.permissionValue);
            picker.addEventListener('click', event => event.stopPropagation());

            const toggle = picker.querySelector('[data-directory-share-permission-toggle]');
            toggle?.addEventListener('click', () => {
                const shouldOpen = !picker.classList.contains('is-open');
                if (shouldOpen) {
                    openDirectorySharePermissionPicker(picker);
                } else {
                    closeDirectorySharePermissionPickers();
                }
            });

            toggle?.addEventListener('keydown', event => {
                if (event.key === 'ArrowDown' || event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    openDirectorySharePermissionPicker(picker, true);
                } else if (event.key === 'Escape') {
                    closeDirectorySharePermissionPickers();
                }
            });

            picker.querySelector('[data-directory-share-permission-hidden]')?.addEventListener('change', event => {
                updateDirectorySharePermissionPicker(picker, event.target.value);
            });

            picker.querySelectorAll('[data-directory-share-permission-option]').forEach(option => {
                option.addEventListener('click', () => selectDirectorySharePermissionOption(option));
                option.addEventListener('keydown', event => {
                    if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        selectDirectorySharePermissionOption(option);
                    } else if (event.key === 'ArrowDown') {
                        event.preventDefault();
                        focusDirectorySharePermissionOption(option, 1);
                    } else if (event.key === 'ArrowUp') {
                        event.preventDefault();
                        focusDirectorySharePermissionOption(option, -1);
                    } else if (event.key === 'Escape') {
                        closeDirectorySharePermissionPickers(null, true);
                    }
                });
            });
        });
    }

    function closeContactCustomSelects(exceptSelect = null, restoreFocus = false) {
        document.querySelectorAll('[data-contact-custom-select].is-open').forEach(selectControl => {
            if (selectControl === exceptSelect) return;
            selectControl.classList.remove('is-open');
            selectControl.querySelector('[data-contact-custom-select-toggle]')?.setAttribute('aria-expanded', 'false');
            const menu = selectControl.querySelector('[data-contact-custom-select-menu]');
            if (menu) menu.hidden = true;
            if (restoreFocus) {
                selectControl.querySelector('[data-contact-custom-select-toggle]')?.focus();
            }
        });
    }

    function getContactCustomSource(selectControl) {
        return selectControl?.querySelector('select') || null;
    }

    function getContactOptionLabel(option) {
        return (option?.textContent || option?.label || '').replace(/\s+/g, ' ').trim() || 'Wybierz';
    }

    function selectedContactCustomOption(selectControl) {
        const source = getContactCustomSource(selectControl);
        if (!source || !source.options.length) return null;
        return source.options[Math.max(0, source.selectedIndex)] || source.options[0];
    }

    function renderContactCustomOptions(selectControl) {
        const source = getContactCustomSource(selectControl);
        const menu = selectControl?.querySelector('[data-contact-custom-select-menu]');
        if (!source || !menu) return;

        menu.replaceChildren();

        Array.from(source.options).forEach((option, index) => {
            const item = document.createElement('button');
            item.type = 'button';
            item.className = 'contacts-custom-select__option';
            item.setAttribute('role', 'option');
            item.dataset.contactCustomSelectOption = '';
            item.dataset.contactCustomSelectIndex = String(index);
            if (option.disabled) item.disabled = true;

            const check = document.createElement('span');
            check.className = 'contacts-custom-select__check';
            check.setAttribute('aria-hidden', 'true');

            const label = document.createElement('span');
            label.className = 'contacts-custom-select__option-label';
            label.textContent = getContactOptionLabel(option);

            item.append(check, label);
            menu.appendChild(item);
        });
    }

    function syncContactCustomSelect(selectControl) {
        const source = getContactCustomSource(selectControl);
        if (!source) return;

        const button = selectControl.querySelector('[data-contact-custom-select-toggle]');
        const label = selectControl.querySelector('[data-contact-custom-select-label]');
        const options = Array.from(selectControl.querySelectorAll('[data-contact-custom-select-option]'));
        const selectedOption = selectedContactCustomOption(selectControl);
        const selectedIndex = selectedOption ? Array.from(source.options).indexOf(selectedOption) : -1;

        if (button) {
            button.disabled = source.disabled || !source.options.length;
        }

        if (label) {
            label.textContent = selectedOption ? getContactOptionLabel(selectedOption) : 'Brak opcji';
        }

        options.forEach((optionButton, index) => {
            const isSelected = index === selectedIndex;
            optionButton.classList.toggle('is-selected', isSelected);
            optionButton.setAttribute('aria-selected', String(isSelected));
            optionButton.tabIndex = isSelected ? 0 : -1;
        });
    }

    function openContactCustomSelect(selectControl, focusSelected = false) {
        const source = getContactCustomSource(selectControl);
        if (!selectControl || !source || source.disabled || !source.options.length) return;

        closeContactCustomSelects(selectControl);
        syncContactCustomSelect(selectControl);
        selectControl.classList.add('is-open');
        selectControl.querySelector('[data-contact-custom-select-toggle]')?.setAttribute('aria-expanded', 'true');
        const menu = selectControl.querySelector('[data-contact-custom-select-menu]');
        if (menu) menu.hidden = false;

        if (focusSelected) {
            const selected = selectControl.querySelector('[data-contact-custom-select-option].is-selected:not(:disabled)')
                || selectControl.querySelector('[data-contact-custom-select-option]:not(:disabled)');
            selected?.focus();
        }
    }

    function selectContactCustomOption(selectControl, optionButton) {
        const source = getContactCustomSource(selectControl);
        if (!source || !optionButton || optionButton.disabled) return;

        const index = Number(optionButton.dataset.contactCustomSelectIndex);
        if (!Number.isInteger(index) || !source.options[index]) return;

        source.selectedIndex = index;
        source.dispatchEvent(new Event('change', { bubbles: true }));
        syncContactCustomSelect(selectControl);
        closeContactCustomSelects(null, true);
    }

    function focusContactCustomOption(selectControl, direction) {
        const options = Array.from(selectControl.querySelectorAll('[data-contact-custom-select-option]:not(:disabled)'));
        if (!options.length) return;

        if (!selectControl.classList.contains('is-open')) {
            openContactCustomSelect(selectControl);
        }

        const focusedIndex = options.indexOf(document.activeElement);
        const selectedIndex = Math.max(0, options.findIndex(option => option.classList.contains('is-selected')));
        const currentIndex = focusedIndex >= 0 ? focusedIndex : selectedIndex;
        const nextIndex = (currentIndex + direction + options.length) % options.length;
        options[nextIndex]?.focus();
    }

    function handleContactCustomSelectKeydown(event) {
        const selectControl = event.target.closest('[data-contact-custom-select]');
        if (!selectControl) return false;

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            focusContactCustomOption(selectControl, 1);
            return true;
        }

        if (event.key === 'ArrowUp') {
            event.preventDefault();
            focusContactCustomOption(selectControl, -1);
            return true;
        }

        if (event.key === 'Home') {
            event.preventDefault();
            openContactCustomSelect(selectControl);
            selectControl.querySelector('[data-contact-custom-select-option]:not(:disabled)')?.focus();
            return true;
        }

        if (event.key === 'End') {
            event.preventDefault();
            openContactCustomSelect(selectControl);
            const options = Array.from(selectControl.querySelectorAll('[data-contact-custom-select-option]:not(:disabled)'));
            options[options.length - 1]?.focus();
            return true;
        }

        if (event.key === 'Escape' && selectControl.classList.contains('is-open')) {
            event.preventDefault();
            closeContactCustomSelects(null, true);
            return true;
        }

        if ((event.key === 'Enter' || event.key === ' ') && event.target.matches('[data-contact-custom-select-option]')) {
            event.preventDefault();
            selectContactCustomOption(selectControl, event.target);
            return true;
        }

        return false;
    }

    function initContactCustomSelects() {
        document.querySelectorAll('[data-contact-custom-select]').forEach(selectControl => {
            if (selectControl.dataset.contactCustomSelectInitialized === 'true') {
                syncContactCustomSelect(selectControl);
                return;
            }

            const source = getContactCustomSource(selectControl);
            if (!source) return;

            source.setAttribute('aria-hidden', 'true');
            source.tabIndex = -1;

            const labelText = selectControl.dataset.contactCustomSelectLabel || source.getAttribute('aria-label') || 'Wybierz';
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'contacts-custom-select__button';
            button.setAttribute('aria-haspopup', 'listbox');
            button.setAttribute('aria-expanded', 'false');
            button.setAttribute('aria-label', labelText);
            button.dataset.contactCustomSelectToggle = '';

            const label = document.createElement('span');
            label.className = 'contacts-custom-select__button-label';
            label.dataset.contactCustomSelectLabel = '';

            const caret = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            caret.setAttribute('class', 'contacts-custom-select__caret');
            caret.setAttribute('viewBox', '0 0 20 20');
            caret.setAttribute('fill', 'none');
            caret.setAttribute('stroke', 'currentColor');
            caret.setAttribute('stroke-width', '1.8');
            caret.setAttribute('stroke-linecap', 'round');
            caret.setAttribute('stroke-linejoin', 'round');
            caret.setAttribute('aria-hidden', 'true');
            const caretPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            caretPath.setAttribute('d', 'm5 7.5 5 5 5-5');
            caret.appendChild(caretPath);

            const menu = document.createElement('div');
            menu.className = 'contacts-custom-select__menu';
            menu.setAttribute('role', 'listbox');
            menu.setAttribute('aria-label', labelText);
            menu.hidden = true;
            menu.dataset.contactCustomSelectMenu = '';

            button.append(label, caret);
            selectControl.append(button, menu);
            renderContactCustomOptions(selectControl);
            syncContactCustomSelect(selectControl);

            button.addEventListener('click', event => {
                event.stopPropagation();
                const isOpen = selectControl.classList.contains('is-open');
                closeCreateMenu();
                closeProjectActionMenus();
                closeSectionActionMenu();
                closeStatusFilterMenu();
                closePriorityFilterMenu();
                closeIssuePickers();
                closeInlineSelectDropdowns();
                closeContactCustomSelects(selectControl);
                if (isOpen) {
                    closeContactCustomSelects();
                } else {
                    openContactCustomSelect(selectControl);
                }
            });

            menu.addEventListener('click', event => {
                event.stopPropagation();
                const optionButton = event.target.closest('[data-contact-custom-select-option]');
                if (optionButton) selectContactCustomOption(selectControl, optionButton);
            });

            source.addEventListener('change', () => syncContactCustomSelect(selectControl));
            selectControl.dataset.contactCustomSelectInitialized = 'true';
        });
    }

    function getPriorityFilterIconMarkup(priority) {
        if (!priority) return '';
        const icons = {
            urgent: 'circle-alert',
            high: 'arrow-up',
            medium: 'equal',
            low: 'arrow-down',
            none: 'circle',
        };
        const icon = icons[priority] || 'circle';
        const iconMarkup = window.AncoreIcons
            ? window.AncoreIcons.html(icon, { fallback: 'circle' })
            : `<i data-lucide="${icon}" data-lucide-fallback="circle" aria-hidden="true"></i>`;
        return `<span class="tasks-row-priority priority-${priority}"><span class="tasks-priority-icon">${iconMarkup}</span></span>`;
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

    function createInlineSelectOptionButton(option, isMultiple) {
        const button = document.createElement('button');
        button.type = 'button';
        button.setAttribute('role', isMultiple ? 'menuitemcheckbox' : 'menuitem');
        button.dataset.inlineSelectValue = option.value;
        if (isMultiple) {
            button.setAttribute('aria-checked', 'false');
            const chip = document.createElement('span');
            chip.className = 'tasks-tag-chip';
            const label = document.createElement('span');
            label.textContent = option.textContent.trim();
            chip.appendChild(label);
            button.appendChild(chip);
        } else {
            const label = document.createElement('span');
            label.textContent = option.textContent.trim();
            button.appendChild(label);
        }
        return button;
    }

    function ensureInlineSelectMenuOptions(dropdown) {
        if (!dropdown || !dropdown.hasAttribute('data-inline-select-lazy')) return;
        if (dropdown.dataset.inlineSelectHydrated === 'true') return;

        const select = getInlineSelect(dropdown);
        const menu = dropdown.querySelector('.tasks-filter-menu');
        if (!select || !menu) return;

        const isMultiple = dropdown.hasAttribute('data-inline-select-multiple');
        const options = Array.from(select.options).filter(option => option.value !== '');
        menu.replaceChildren();
        if (!options.length) {
            const emptyButton = document.createElement('button');
            emptyButton.type = 'button';
            emptyButton.disabled = true;
            emptyButton.setAttribute('role', 'menuitem');
            const label = document.createElement('span');
            label.textContent = dropdown.dataset.inlineSelectEmptyLabel || 'Brak opcji';
            emptyButton.appendChild(label);
            menu.appendChild(emptyButton);
        } else {
            options.forEach(option => {
                menu.appendChild(createInlineSelectOptionButton(option, isMultiple));
            });
        }
        dropdown.dataset.inlineSelectHydrated = 'true';
    }

    function createSelectedTagChip(option) {
        const chip = document.createElement('span');
        chip.className = 'tasks-tag-chip';
        const label = document.createElement('span');
        label.textContent = option.textContent.trim();
        chip.appendChild(label);
        return chip;
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
            const activeButtons = dropdown.querySelectorAll('[data-inline-select-value].is-active');
            activeButtons.forEach(button => {
                const chip = button.querySelector('.tasks-tag-chip')?.cloneNode(true);
                if (chip) selectedTags.appendChild(chip);
            });
            if (!activeButtons.length && selectedValues.length) {
                Array.from(select.selectedOptions).forEach(option => {
                    selectedTags.appendChild(createSelectedTagChip(option));
                });
            }
        }

        if (statusIcon) {
            statusIcon.className = `status-indicator tasks-filter-status-icon ${currentValue ? `status-${currentValue}` : 'status-label-plain'}`;
        }

        if (priorityIcon) {
            priorityIcon.innerHTML = getPriorityFilterIconMarkup(currentValue);
            window.AncoreIcons?.render(priorityIcon);
        }
    }

    function syncInlineSelectForSelect(select) {
        const dropdown = select?.closest('.tasks-issue-select-wrap')?.querySelector('[data-inline-select-dropdown]');
        syncInlineSelectDropdown(dropdown);
    }

    function closeIssuePickers(exceptPicker = null) {
        [issueProjectPicker, issueSectionPicker].forEach(picker => {
            if (!picker || picker === exceptPicker) return;
            picker.classList.remove('is-open');
            picker.querySelector('[data-picker-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    function parseIssuePickerOptions() {
        const dataScript = issueForm?.querySelector('#issue-picker-options');
        if (!dataScript?.textContent) return [];
        try {
            const parsed = JSON.parse(dataScript.textContent);
            if (!Array.isArray(parsed)) return [];
            return parsed.map(project => ({
                projectId: String(project.projectId || ''),
                projectName: project.projectName || '',
                projectIcon: project.projectIcon || '',
                projectColor: project.projectColor || '',
                defaultSectionId: String(project.defaultSectionId || ''),
                sections: Array.isArray(project.sections)
                    ? project.sections.map(section => ({
                        sectionId: String(section.sectionId || ''),
                        sectionProjectId: String(section.sectionProjectId || project.projectId || ''),
                        sectionTitle: section.sectionTitle || '',
                        sectionIcon: section.sectionIcon || '',
                    }))
                    : [],
            })).filter(project => project.projectId);
        } catch (error) {
            return [];
        }
    }

    function getIssueProjectRecords() {
        if (issuePickerOptionsData.length) return issuePickerOptionsData;
        return issueProjectOptions.map(option => option.dataset);
    }

    function getIssueSectionRecords() {
        if (issueSectionOptionsData.length) return issueSectionOptionsData;
        return issueSectionOptions.map(option => option.dataset);
    }

    function findIssueProjectRecord(projectId) {
        const records = getIssueProjectRecords();
        const selectedId = String(projectId || '');
        return records.find(project => project.projectId === selectedId) || records[0] || null;
    }

    function findIssueSectionRecord(sectionId) {
        const selectedId = String(sectionId || '');
        if (!selectedId) return null;
        return getIssueSectionRecords().find(section => section.sectionId === selectedId) || null;
    }

    function createIssueProjectOption(project) {
        const button = document.createElement('button');
        button.type = 'button';
        button.setAttribute('role', 'menuitem');
        button.dataset.projectOption = '';
        button.dataset.projectId = project.projectId;
        button.dataset.projectName = project.projectName;
        button.dataset.projectIcon = project.projectIcon;
        button.dataset.projectColor = project.projectColor;
        button.dataset.defaultSectionId = project.defaultSectionId || '';

        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        if (project.projectColor) icon.style.setProperty('--project-icon-fg', project.projectColor);
        if (project.projectIcon) icon.appendChild(createProjectIconElement(project.projectIcon));
        button.append(icon, document.createTextNode(project.projectName));
        return button;
    }

    function createIssueSectionOption(section) {
        const button = document.createElement('button');
        button.type = 'button';
        button.setAttribute('role', 'menuitem');
        button.dataset.sectionOption = '';
        button.dataset.sectionId = section.sectionId;
        button.dataset.sectionProjectId = section.sectionProjectId;
        button.dataset.sectionTitle = section.sectionTitle;
        button.dataset.sectionIcon = section.sectionIcon;

        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        if (section.sectionIcon) icon.appendChild(createProjectIconElement(section.sectionIcon));
        button.append(icon, document.createTextNode(section.sectionTitle));
        return button;
    }

    function appendEmptyIssuePickerOption(menu, labelText) {
        const button = document.createElement('button');
        button.type = 'button';
        button.disabled = true;
        button.setAttribute('role', 'menuitem');
        const label = document.createElement('span');
        label.textContent = labelText;
        button.appendChild(label);
        menu.appendChild(button);
    }

    function hydrateIssuePickerOptions() {
        if (issuePickerOptionsHydrated || !issuePickerOptionsData.length) return;
        const projectMenu = issueProjectPicker?.querySelector('.tasks-chip-picker__menu');
        const sectionMenu = issueSectionPicker?.querySelector('.tasks-chip-picker__menu');
        if (!projectMenu || !sectionMenu) return;

        projectMenu.querySelectorAll('[data-project-option]').forEach(option => option.remove());
        sectionMenu.querySelectorAll('[data-section-option]').forEach(option => option.remove());

        if (issuePickerOptionsData.length) {
            issuePickerOptionsData.forEach(project => {
                projectMenu.appendChild(createIssueProjectOption(project));
            });
        } else {
            appendEmptyIssuePickerOption(projectMenu, 'Brak projektów');
        }

        if (issueSectionOptionsData.length) {
            issueSectionOptionsData.forEach(section => {
                sectionMenu.appendChild(createIssueSectionOption(section));
            });
        } else {
            appendEmptyIssuePickerOption(sectionMenu, 'Brak grup');
        }

        issueProjectOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-project-option]')) : [];
        issueSectionOptions = issueForm ? Array.from(issueForm.querySelectorAll('[data-section-option]')) : [];
        issuePickerOptionsHydrated = true;
        renderLucideIcons(projectMenu);
        renderLucideIcons(sectionMenu);
    }

    function normalizePickerSearch(value) {
        return (value || '').trim().toLowerCase();
    }

    function filterPickerSearch(input) {
        const query = normalizePickerSearch(input?.value);
        const type = input?.dataset.pickerSearchType || '';
        const selectedProjectId = issueProjectInput?.value || '';

        if (type === 'project') {
            getIssueProjectRecords().forEach(project => {
                const option = issueProjectOptions.find(item => item.dataset.projectId === project.projectId);
                const text = normalizePickerSearch(project.projectName || option?.textContent);
                if (option) option.hidden = query ? !text.includes(query) : false;
            });
            return;
        }

        if (type === 'section') {
            getIssueSectionRecords().forEach(section => {
                const option = issueSectionOptions.find(item => item.dataset.sectionId === section.sectionId);
                const belongsToProject = !selectedProjectId || section.sectionProjectId === selectedProjectId;
                const text = normalizePickerSearch(section.sectionTitle || option?.textContent);
                if (option) option.hidden = !belongsToProject || (query ? !text.includes(query) : false);
            });
        }
    }

    function resetPickerSearch(picker) {
        const input = picker?.querySelector('[data-picker-search]');
        if (!input) return;
        input.value = '';
        filterPickerSearch(input);
    }

    function getProjectTreeCollapsed() {
        try {
            return localStorage.getItem(projectTreeStorageKey) === 'true';
        } catch (error) {
            return false;
        }
    }

    function saveProjectTreeCollapsed(isCollapsed) {
        try {
            localStorage.setItem(projectTreeStorageKey, String(isCollapsed));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function getCollapsedProjects() {
        try {
            return new Set(JSON.parse(localStorage.getItem(collapsedProjectsStorageKey) || '[]'));
        } catch (error) {
            return new Set();
        }
    }

    function saveCollapsedProjects(collapsedProjects) {
        try {
            localStorage.setItem(collapsedProjectsStorageKey, JSON.stringify([...collapsedProjects]));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function getCollapsedRailNavGroups() {
        try {
            return new Set(JSON.parse(localStorage.getItem('collapsedTaskRailNavGroups') || '[]'));
        } catch (error) {
            return new Set();
        }
    }

    function saveCollapsedRailNavGroups(collapsedGroups) {
        try {
            localStorage.setItem('collapsedTaskRailNavGroups', JSON.stringify([...collapsedGroups]));
        } catch (error) {
            // Ignore storage failures; the in-page collapse state still works.
        }
    }

    function setRailNavGroupCollapsed(group, isCollapsed) {
        const toggle = group.querySelector('[data-rail-nav-group-toggle]');
        const label = toggle?.querySelector('span')?.textContent?.trim() || 'sekcję';

        group.classList.toggle('is-collapsed', isCollapsed);
        toggle?.setAttribute('aria-expanded', String(!isCollapsed));
        toggle?.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} sekcję ${label}`);
    }

    function setProjectTreeCollapsed(isCollapsed) {
        if (!projectTree || !projectTreeToggle) return;

        const treeLabel = projectTreeToggle.dataset.projectTreeLabel
            || projectTreeToggle.querySelector('.tasks-project-tree-label, span')?.textContent?.trim()
            || 'projekty';

        projectTree.classList.toggle('is-collapsed', isCollapsed);
        projectTreeToggle.setAttribute('aria-expanded', String(!isCollapsed));
        projectTreeToggle.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} sekcję ${treeLabel}`);
    }

    function setProjectCollapsed(projectNode, isCollapsed) {
        const toggle = projectNode.querySelector('[data-project-collapse-toggle]');
        const projectKindAcc = taskAppSegment === 'kanban' ? 'przestrzeń roboczą' : 'projekt';
        const projectName = projectNode.querySelector('.tasks-project-title span:not(.tasks-project-badge)')?.textContent?.trim() || 'bez nazwy';

        projectNode.classList.toggle('is-collapsed', isCollapsed);
        toggle?.setAttribute('aria-expanded', String(!isCollapsed));
        toggle?.setAttribute('aria-label', `${isCollapsed ? 'Rozwiń' : 'Zwiń'} ${projectKindAcc} ${projectName}`);
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
        window.AncoreCustomSelect?.refresh(modal);
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

    function getLucideProjectIcon(icon, fallback = 'folder') {
        if (!icon) return fallback;
        return window.AncoreIcons ? window.AncoreIcons.safeName(icon, fallback) : icon;
    }

    function createProjectIconElement(icon, fallback = 'folder', className = '') {
        const iconName = getLucideProjectIcon(icon, fallback);
        if (window.AncoreIcons) {
            return window.AncoreIcons.create(iconName, { fallback, className });
        }
        const element = document.createElement('i');
        element.setAttribute('data-lucide', iconName);
        element.setAttribute('data-lucide-fallback', fallback);
        element.setAttribute('aria-hidden', 'true');
        if (className) element.className = className;
        return element;
    }

    function createSectionDefaultIconSvg() {
        return createProjectIconElement('circle-check', 'circle-check', 'tasks-section-default-icon');
    }

    function createEmptyIconSvg() {
        return createProjectIconElement('circle-dashed', 'circle-dashed', 'tasks-empty-icon');
    }

    function renderLucideIcons(root) {
        window.AncoreIcons?.render(root || document);
    }

    function renderProjectIcon(display, icon) {
        if (!display) return;
        display.replaceChildren();
        if (!icon) {
            display.appendChild(createEmptyIconSvg());
            renderLucideIcons(display);
            return;
        }
        if (icon === 'check' || icon === 'circle-check') {
            display.appendChild(createSectionDefaultIconSvg());
            renderLucideIcons(display);
            return;
        }
        display.appendChild(createProjectIconElement(icon));
        renderLucideIcons(display);
    }

    function setIconValue(input, picker, icon) {
        const trimmedIcon = (icon || '').trim();
        const normalizedIcon = trimmedIcon ? getLucideProjectIcon(trimmedIcon) : '';
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
        if (iconEl) {
            iconEl.replaceChildren();
            if (icon) iconEl.appendChild(createProjectIconElement(icon));
            renderLucideIcons(iconEl);
        }
        if (toggle && color) toggle.style.setProperty('--project-icon-fg', color);
    }

    function getSelectedSectionOption() {
        if (!issueSectionSelect?.value) return null;
        return findIssueSectionRecord(issueSectionSelect.value);
    }

    function selectIssueSection(sectionId) {
        const sectionOption = findIssueSectionRecord(sectionId);
        if (!sectionOption || !issueSectionSelect) return false;

        issueSectionSelect.value = sectionOption.sectionId || '';
        setIssueChip(issueSectionPicker, sectionOption.sectionTitle || sectionCopy.emptyLabel, sectionOption.sectionIcon || '');
        return true;
    }

    function filterIssueSections(projectId) {
        let firstVisibleSectionId = '';
        const sectionSearch = issueSectionPicker?.querySelector('[data-picker-search]');
        const query = normalizePickerSearch(sectionSearch?.value);

        getIssueSectionRecords().forEach(section => {
            const option = issueSectionOptions.find(item => item.dataset.sectionId === section.sectionId);
            const text = normalizePickerSearch(section.sectionTitle || option?.textContent);
            const isVisible = (!projectId || section.sectionProjectId === String(projectId)) && (!query || text.includes(query));
            if (option) option.hidden = !isVisible;
            if (isVisible && !firstVisibleSectionId) {
                firstVisibleSectionId = section.sectionId || '';
            }
        });

        return firstVisibleSectionId;
    }

    function selectIssueProject(projectId, preferredSectionId = '') {
        const projectOption = findIssueProjectRecord(projectId);
        if (!projectOption) return;

        const selectedProjectId = projectOption.projectId || '';
        if (issueProjectInput) issueProjectInput.value = selectedProjectId;
        setIssueChip(
            issueProjectPicker,
            projectOption.projectName || 'Wybierz przestrzeń',
            projectOption.projectIcon || '',
            projectOption.projectColor || ''
        );

        const firstVisibleSectionId = filterIssueSections(selectedProjectId);
        const currentSectionOption = getSelectedSectionOption();
        const currentSectionFits = currentSectionOption?.sectionProjectId === selectedProjectId;
        const nextSectionId = preferredSectionId || (currentSectionFits ? currentSectionOption.sectionId : '') || projectOption.defaultSectionId || firstVisibleSectionId;

        if (!selectIssueSection(nextSectionId) && firstVisibleSectionId) {
            selectIssueSection(firstVisibleSectionId);
        }
    }

    function syncIssuePickers() {
        const projectOptions = getIssueProjectRecords();
        if (!issueForm || !projectOptions.length) return;

        const selectedSectionOption = getSelectedSectionOption();
        const projectId = issueProjectInput?.value || selectedSectionOption?.sectionProjectId || projectOptions[0]?.projectId || '';
        selectIssueProject(projectId, selectedSectionOption?.sectionId || '');
    }

    function selectIssueSectionContext(sectionId) {
        if (!sectionId) return false;
        const sectionOption = findIssueSectionRecord(sectionId);
        if (!sectionOption) return false;

        selectIssueProject(sectionOption.sectionProjectId || '', sectionId);
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
            tab.appendChild(createProjectIconElement(set.icon, 'icons'));
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
        searchWrap.innerHTML = window.AncoreIcons
            ? window.AncoreIcons.html('search')
            : '<i data-lucide="search" aria-hidden="true"></i>';

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
        clearButton.innerHTML = AttachmentIcons.TRASH_SVG;
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
        renderLucideIcons(emojiPicker);
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
                .filter(item => getLucideProjectIcon(item.icon).includes(query) || item.keywords.includes(query))
                .map(item => getLucideProjectIcon(item.icon))
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
                const iconName = getLucideProjectIcon(icon, 'circle');
                const option = document.createElement('button');
                option.type = 'button';
                option.className = 'tasks-emoji-option';
                option.appendChild(createProjectIconElement(iconName, 'circle'));
                option.setAttribute('aria-label', `Wybierz ikonę ${iconName}`);
                option.title = iconName;
                option.addEventListener('click', () => {
                    setIconValue(activeIconInput, activeIconPicker, iconName);
                    closeEmojiPicker();
                    activeIconInput?.focus();
                });
                list.appendChild(option);
            });

            group.appendChild(title);
            group.appendChild(list);
            emojiPickerBody.appendChild(group);
        });
        renderLucideIcons(emojiPickerBody);
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
            closeDirectoryMembersMenus();
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
            closeProjectFilterMenus();
            closeProjectSortMenu();
            closeDirectoryMembersMenus();
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
            closeProjectFilterMenus();
            closeProjectSortMenu();
            closeDirectoryMembersMenus();
            priorityFilterMenu.classList.toggle('is-open', isOpen);
            priorityFilterToggle.setAttribute('aria-expanded', String(isOpen));
        });

        priorityFilterMenu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    }

    function openDirectoryShareModal(button) {
        if (!directoryShareModal || !directoryShareForm) return;
        const action = button.dataset.shareAction || '';
        const projectId = button.dataset.shareProjectId || '';
        const sectionId = button.dataset.shareSectionId || '';
        const taskId = button.dataset.shareTaskId || '';
        const objectKind = button.dataset.shareObjectKind || '';
        const objectId = button.dataset.shareObjectId || '';
        const linkUrl = button.dataset.shareLinkUrl || '';
        const linkPermission = button.dataset.shareLinkPermission || 'view';
        const objectType = button.dataset.shareObjectType || '';
        const objectName = button.dataset.shareObjectName || '';
        const canManageShare = button.dataset.shareCanManage !== 'false';

        if (directoryShareActionInput) directoryShareActionInput.value = action;
        if (directoryShareProjectInput) directoryShareProjectInput.value = projectId;
        if (directoryShareSectionInput) directoryShareSectionInput.value = sectionId;
        if (directoryShareTaskInput) directoryShareTaskInput.value = taskId;
        if (directoryShareObjectTypeInput) directoryShareObjectTypeInput.value = objectKind;
        if (directoryShareObjectIdInput) directoryShareObjectIdInput.value = objectId;
        if (directoryShareMemberIdInput) directoryShareMemberIdInput.value = '';
        if (directorySharePermissionInput) directorySharePermissionInput.value = linkPermission === 'edit' ? 'edit' : 'view';
        setDirectoryShareManageState(canManageShare);
        syncDirectorySharePermissionPickers(directoryShareForm);
        directorySharePersonInputs.forEach(input => { input.value = ''; });
        directoryShareSearchValue = '';
        setDirectoryShareSelectedValues([]);
        updateDirectoryShareLinkState(linkUrl);
        syncDirectoryShareResults();
        setDirectoryShareContactsOpen(false);
        renderDirectoryShareMembers(button.dataset.shareMembersTemplate || '');
        if (directoryShareContext) {
            directoryShareContext.textContent = [objectType, objectName].filter(Boolean).join(': ');
        }

        closeCreateMenu();
        closeProjectActionMenus();
        closeSectionActionMenu();
        closeStatusFilterMenu();
        closePriorityFilterMenu();
        closeInlineSelectDropdowns();
        closeDirectoryMembersMenus();
        openModal(directoryShareModal, directoryShareMemberInput, updateDirectoryShareSubmitState);
    }

    directoryShareButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            openDirectoryShareModal(this);
        });
    });

    directoryMembersMenus.forEach(menu => {
        const toggle = menu.querySelector('[data-directory-members-toggle]');

        toggle?.addEventListener('click', function(e) {
            e.stopPropagation();
            if (toggle.hasAttribute('data-directory-share-open')) {
                openDirectoryShareModal(toggle);
                return;
            }
            const isOpen = !menu.classList.contains('is-open');
            const searchInput = menu.querySelector('[data-directory-members-search]');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeInlineSelectDropdowns();
            closeDirectoryMembersMenus(menu);
            if (searchInput) searchInput.value = '';
            filterDirectoryMembers(menu);
            menu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        menu.addEventListener('click', function(e) {
            e.stopPropagation();
        });
    });

    document.querySelectorAll('[data-directory-member-actions]').forEach(details => {
        details.addEventListener('toggle', function() {
            if (!this.open) return;
            const popover = this.closest('[data-directory-members-popover]');
            popover?.querySelectorAll('[data-directory-member-actions][open]').forEach(otherDetails => {
                if (otherDetails !== this) otherDetails.removeAttribute('open');
            });
        });
    });

    directoryMembersSearchInputs.forEach(input => {
        input.addEventListener('input', function() {
            filterDirectoryMembers(this.closest('[data-directory-members-menu]'));
        });
    });

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
            if (isOpen) {
                ensureInlineSelectMenuOptions(dropdown);
                syncInlineSelectDropdown(dropdown);
            }
            dropdown.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        });

        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
            const button = e.target.closest('[data-inline-select-value]');
            if (!button || !dropdown.contains(button) || !select) return;

            if (isMultiple) {
                const option = Array.from(select.options).find(item => item.value === button.dataset.inlineSelectValue);
                if (option) option.selected = !option.selected;
            } else {
                select.value = button.dataset.inlineSelectValue;
                closeInlineSelectDropdowns();
            }

            select.dispatchEvent(new Event('change', { bubbles: true }));
            syncInlineSelectDropdown(dropdown);
        });

        select?.addEventListener('change', function() {
            syncInlineSelectDropdown(dropdown);
        });
    });

    document.querySelectorAll('[data-company-select-dropdown]').forEach(dropdown => {
        const select = dropdown.closest('.tasks-company-select-wrap')?.querySelector('select');
        const toggle = dropdown.querySelector('[data-company-select-toggle]');
        const menu = getCompanySelectMenu(dropdown);
        const search = menu?.querySelector('[data-company-select-search]');

        syncCompanySelectDropdown(dropdown);

        toggle?.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !dropdown.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeIssuePickers();
            closeInlineSelectDropdowns();
            closeCompanySelectDropdowns(dropdown);
            dropdown.classList.toggle('is-open', isOpen);
            menu?.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
            if (isOpen) {
                if (search) search.value = '';
                filterCompanySelectOptions(dropdown);
                setTimeout(() => search?.focus(), 30);
            }
        });

        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        menu?.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        search?.addEventListener('input', function() {
            filterCompanySelectOptions(dropdown);
        });

        menu?.querySelectorAll('[data-company-select-value]').forEach(button => {
            button.addEventListener('click', function(e) {
                if (!select) return;
                const clearTarget = e.target.closest('[data-company-select-clear]');
                select.value = clearTarget && this.classList.contains('is-active') ? '' : this.dataset.companySelectValue || '';
                select.dispatchEvent(new Event('change', { bubbles: true }));
                syncCompanySelectDropdown(dropdown);
                closeCompanySelectDropdowns();
            });
        });

        select?.addEventListener('change', function() {
            syncCompanySelectDropdown(dropdown);
        });
    });

    document.querySelectorAll('[data-responsible-select-dropdown]').forEach(dropdown => {
        const wrap = dropdown.closest('.tasks-responsible-select-wrap');
        const select = wrap?.querySelector('select');
        const toggle = dropdown.querySelector('[data-responsible-select-toggle]');
        const menu = getResponsibleSelectMenu(dropdown);
        const search = menu?.querySelector('[data-responsible-select-search]');
        const saveButton = menu?.querySelector('[data-responsible-select-save]');
        const cancelButton = menu?.querySelector('[data-responsible-select-cancel]');
        const lookupUrl = wrap?.dataset.responsibleSelectUrl || '';
        let lookupTimer = null;
        let lookupController = null;

        syncResponsibleSelectDropdown(dropdown);

        function lookupResponsibleUser() {
            const query = (search?.value || '').trim();
            filterResponsibleSelectOptions(dropdown);
            if (lookupTimer) window.clearTimeout(lookupTimer);
            lookupController?.abort();
            if (!query || query.length < 2 || !lookupUrl) {
                setResponsibleSelectStatus(dropdown);
                return;
            }

            lookupTimer = window.setTimeout(() => {
                lookupController = new AbortController();
                setResponsibleSelectStatus(dropdown, 'Szukam po ID Ancore...', 'loading');
                const url = `${lookupUrl}?q=${encodeURIComponent(query)}`;
                fetch(url, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    signal: lookupController.signal
                })
                    .then(response => response.ok ? response.json() : Promise.reject(new Error('lookup failed')))
                    .then(data => {
                        if (!data.found || !data.user) {
                            setResponsibleSelectStatus(dropdown, data.message || 'Nie znaleziono osoby po ID Ancore.', 'error');
                            return;
                        }
                        ensureResponsibleSelectOption(select, data.user);
                        ensureResponsibleSelectButton(dropdown, data.user);
                        filterResponsibleSelectOptions(dropdown);
                        setResponsibleSelectStatus(dropdown, `Znaleziono: ${data.user.label || data.user.username}. Wybierz osobę z listy.`, 'success');
                    })
                    .catch(error => {
                        if (error.name === 'AbortError') return;
                        setResponsibleSelectStatus(dropdown, 'Nie udało się sprawdzić ID Ancore.', 'error');
                    });
            }, 300);
        }

        toggle?.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !dropdown.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeIssuePickers();
            closeInlineSelectDropdowns();
            closeCompanySelectDropdowns();
            closeResponsibleSelectDropdowns(dropdown);
            dropdown.classList.toggle('is-open', isOpen);
            menu?.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
            if (isOpen) {
                if (search) search.value = '';
                setResponsibleSelectDraft(dropdown, select?.value || '');
                filterResponsibleSelectOptions(dropdown);
                setResponsibleSelectStatus(dropdown);
                setTimeout(() => search?.focus(), 30);
            }
        });

        dropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        menu?.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        search?.addEventListener('input', lookupResponsibleUser);

        menu?.addEventListener('click', function(e) {
            const button = e.target.closest('[data-responsible-select-value]');
            if (!button) return;
            if (!select) return;
            select.value = button.dataset.responsibleSelectValue || '';
            select.dispatchEvent(new Event('change', { bubbles: true }));
            syncResponsibleSelectDropdown(dropdown);
            setResponsibleSelectStatus(dropdown);
            closeResponsibleSelectDropdowns();
        });

        cancelButton?.addEventListener('click', function() {
            setResponsibleSelectDraft(dropdown, select?.value || '');
            closeResponsibleSelectDropdowns();
        });

        saveButton?.addEventListener('click', function() {
            if (!select) return;
            select.value = dropdown.dataset.responsibleDraftValue || '';
            select.dispatchEvent(new Event('change', { bubbles: true }));
            syncResponsibleSelectDropdown(dropdown);
            closeResponsibleSelectDropdowns();
        });

        select?.addEventListener('change', function() {
            syncResponsibleSelectDropdown(dropdown);
        });
    });

    initContactCustomSelects();
    initDirectorySharePermissionPickers(directoryShareForm || document);

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

    if (railNavGroups.length) {
        const collapsedRailNavGroups = getCollapsedRailNavGroups();

        railNavGroups.forEach(group => {
            const groupKey = group.dataset.railNavGroup || '';
            const toggle = group.querySelector('[data-rail-nav-group-toggle]');
            const shouldCollapse = collapsedRailNavGroups.has(groupKey) && !group.classList.contains('is-current');

            setRailNavGroupCollapsed(group, shouldCollapse);

            toggle?.addEventListener('click', function(e) {
                e.preventDefault();

                const isCollapsed = !group.classList.contains('is-collapsed');
                setRailNavGroupCollapsed(group, isCollapsed);

                if (groupKey) {
                    if (isCollapsed) {
                        collapsedRailNavGroups.add(groupKey);
                    } else {
                        collapsedRailNavGroups.delete(groupKey);
                    }
                    saveCollapsedRailNavGroups(collapsedRailNavGroups);
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

    function setMultiSelectValues(select, value) {
        if (!select) return;
        const selectedValues = new Set(String(value || '').split(',').map(item => item.trim()).filter(Boolean));
        Array.from(select.options).forEach(option => {
            option.selected = selectedValues.has(option.value);
        });
    }

    function setTagModalMode(mode, data = {}) {
        const isEdit = mode === 'edit';
        if (tagActionInput) tagActionInput.value = isEdit ? 'edit_tag' : 'create_tag';
        if (tagIdInput) tagIdInput.value = isEdit ? (data.tagId || '') : '';
        if (tagNameInput) tagNameInput.value = isEdit ? (data.tagName || '') : '';
        if (tagDescriptionInput) tagDescriptionInput.value = isEdit ? (data.tagDescription || '') : '';
        if (tagCategoryInput) tagCategoryInput.value = isEdit ? (data.tagCategory || 'general') : 'general';
        if (tagColorInput) tagColorInput.value = isEdit ? (data.tagColor || '#64748b') : '#64748b';
        if (tagIconInput) tagIconInput.value = isEdit ? (data.tagIcon || 'tag') : 'tag';
        if (tagPriorityInput) tagPriorityInput.value = isEdit ? (data.tagPriority || 'none') : 'none';
        if (tagScopeInput) tagScopeInput.value = isEdit ? (data.tagScope || 'tasks') : 'tasks';
        if (tagOwnerInput) tagOwnerInput.value = isEdit ? (data.tagOwnerLabel || '') : '';
        if (tagStatusInput) tagStatusInput.value = isEdit ? (data.tagStatus || 'active') : 'active';
        if (tagUsageNotesInput) tagUsageNotesInput.value = isEdit ? (data.tagUsageNotes || '') : '';
        if (tagAutomationRulesInput) tagAutomationRulesInput.value = isEdit ? (data.tagAutomationRules || '') : '';
        setMultiSelectValues(tagRelatedTagsInput, isEdit ? data.tagRelatedTags : '');
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

    openTagInfoButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.stopPropagation();
            openProjectInfoPanel(button);
        });
    });

    function setFieldValue(input, value) {
        if (!input) return;
        if ('value' in input) {
            input.value = value || '';
            return;
        }
        input.textContent = value || '';
    }

    function setProjectRenameFieldsFromDataset(dataset = {}) {
        setFieldValue(projectRenameIdInput, dataset.projectId);
        setFieldValue(projectRenameNameInput, dataset.projectName);
        setFieldValue(projectRenameDescriptionInput, dataset.projectDescription);
        setFieldValue(projectRenameCompanyInput, dataset.projectCompanyId);
        setFieldValue(projectRenameResponsibleInput, dataset.projectResponsibleUserId);
        setFieldValue(projectRenameStatusInput, dataset.projectStatus || 'active');
        setFieldValue(projectRenameStageInput, dataset.projectStage || 'implementation');
        setFieldValue(projectRenameHealthInput, dataset.projectHealth || 'ok');
        setFieldValue(projectRenamePriorityInput, dataset.projectPriority || 'none');
        syncInlineSelectForSelect(projectRenamePriorityInput);
        setFieldValue(projectRenameStartAtInput, dataset.projectStartAt);
        setFieldValue(projectRenameDueAtInput, dataset.projectDueAt);
        setFieldValue(projectRenameBudgetInput, dataset.projectBudgetAmount);
        setFieldValue(projectRenameCurrencyInput, dataset.projectCurrency || 'PLN');
        setFieldValue(projectRenameSourceInput, dataset.projectSource);
        setFieldValue(projectRenameCodeValue, dataset.projectCode);
        setFieldValue(projectRenameIconInput, dataset.projectIcon);
    }

    openProjectRenameButtons.forEach(button => {
        button.addEventListener('click', () => {
            setProjectRenameFieldsFromDataset(button.dataset);
            syncProjectIconPickers();
            closeProjectActionMenus();
            openModal(projectRenameModal, projectRenameNameInput, updateProjectRenameSubmitState);
            setTimeout(() => projectRenameNameInput?.select(), 60);
        });
    });

    function openProjectNotesModal(button) {
        if (!projectNotesModal || !button) return;

        const row = button.closest('.tasks-project-row') || button.closest('.tasks-directory-row');
        const projectId = button.dataset.projectId || row?.dataset.projectId || '';
        const projectName = button.dataset.projectName || row?.dataset.projectName || '';
        if (projectNotesIdInput) projectNotesIdInput.value = projectId;
        if (projectNotesNameInput) projectNotesNameInput.textContent = projectName || 'Projekt';
        if (projectNotesMessageInput) projectNotesMessageInput.value = '';
        projectNotesThreads.forEach(thread => {
            thread.hidden = thread.dataset.projectId !== projectId;
        });
        closeProjectActionMenus();
        openModal(projectNotesModal, projectNotesMessageInput);
    }

    openProjectNotesButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            openProjectNotesModal(button);
        });
    });

    projectNotesModal?.querySelectorAll('[data-project-note-edit-toggle]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const item = button.closest('[data-project-note-item]');
            const form = item?.querySelector('[data-project-note-edit-form]');
            const input = form?.querySelector('[data-project-note-edit-input]');
            if (!form) return;
            form.hidden = false;
            item.classList.add('is-editing');
            setTimeout(() => {
                input?.focus();
                input?.setSelectionRange?.(input.value.length, input.value.length);
            }, 30);
        });
    });

    projectNotesModal?.querySelectorAll('[data-project-note-edit-cancel]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const item = button.closest('[data-project-note-item]');
            const form = item?.querySelector('[data-project-note-edit-form]');
            if (!form) return;
            const input = form.querySelector('[data-project-note-edit-input]');
            if (input) input.value = input.defaultValue || '';
            form.hidden = true;
            item?.classList.remove('is-editing');
        });
    });

    projectNotesModal?.querySelectorAll('[data-project-note-delete-form]').forEach(form => {
        form.addEventListener('submit', event => {
            if (!window.confirm('Usunąć tę notatkę?')) {
                event.preventDefault();
            }
        });
    });

    function openSectionNotesModal(button) {
        if (!sectionNotesModal || !button) return;

        const row = button.closest('.tasks-section-row') || button.closest('.tasks-directory-row');
        const sectionId = button.dataset.sectionId || row?.dataset.sectionId || '';
        const sectionName = button.dataset.sectionTitle || row?.dataset.sectionTitle || '';
        if (sectionNotesIdInput) sectionNotesIdInput.value = sectionId;
        if (sectionNotesNameInput) sectionNotesNameInput.textContent = sectionName || 'Grupa';
        if (sectionNotesMessageInput) sectionNotesMessageInput.value = '';
        sectionNotesThreads.forEach(thread => {
            thread.hidden = thread.dataset.sectionId !== sectionId;
        });
        closeProjectActionMenus();
        openModal(sectionNotesModal, sectionNotesMessageInput);
    }

    openSectionNotesButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            openSectionNotesModal(button);
        });
    });

    sectionNotesModal?.querySelectorAll('[data-section-note-edit-toggle]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const item = button.closest('[data-section-note-item]');
            const form = item?.querySelector('[data-section-note-edit-form]');
            const input = form?.querySelector('[data-section-note-edit-input]');
            if (!form) return;
            form.hidden = false;
            item.classList.add('is-editing');
            setTimeout(() => {
                input?.focus();
                input?.setSelectionRange?.(input.value.length, input.value.length);
            }, 30);
        });
    });

    sectionNotesModal?.querySelectorAll('[data-section-note-edit-cancel]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const item = button.closest('[data-section-note-item]');
            const form = item?.querySelector('[data-section-note-edit-form]');
            if (!form) return;
            const input = form.querySelector('[data-section-note-edit-input]');
            if (input) input.value = input.defaultValue || '';
            form.hidden = true;
            item?.classList.remove('is-editing');
        });
    });

    sectionNotesModal?.querySelectorAll('[data-section-note-delete-form]').forEach(form => {
        form.addEventListener('submit', event => {
            if (!window.confirm('Usunąć tę notatkę?')) {
                event.preventDefault();
            }
        });
    });

    function openTagNotesModal(button) {
        if (!tagNotesModal || !button) return;

        const row = button.closest('.tasks-tag-sheet__row') || button.closest('.tasks-directory-row');
        const tagId = button.dataset.tagId || row?.dataset.tagId || '';
        const tagName = button.dataset.tagName || row?.dataset.tagName || '';
        if (tagNotesIdInput) tagNotesIdInput.value = tagId;
        if (tagNotesNameInput) tagNotesNameInput.textContent = tagName || 'Tag';
        if (tagNotesMessageInput) tagNotesMessageInput.value = '';
        tagNotesThreads.forEach(thread => {
            thread.hidden = thread.dataset.tagId !== tagId;
        });
        closeProjectActionMenus();
        openModal(tagNotesModal, tagNotesMessageInput);
    }

    openTagNotesButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            openTagNotesModal(button);
        });
    });

    tagNotesModal?.querySelectorAll('[data-tag-note-edit-toggle]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const item = button.closest('[data-tag-note-item]');
            const form = item?.querySelector('[data-tag-note-edit-form]');
            const input = form?.querySelector('[data-tag-note-edit-input]');
            if (!form) return;
            form.hidden = false;
            item.classList.add('is-editing');
            setTimeout(() => {
                input?.focus();
                input?.setSelectionRange?.(input.value.length, input.value.length);
            }, 30);
        });
    });

    tagNotesModal?.querySelectorAll('[data-tag-note-edit-cancel]').forEach(button => {
        button.addEventListener('click', event => {
            event.preventDefault();
            const item = button.closest('[data-tag-note-item]');
            const form = item?.querySelector('[data-tag-note-edit-form]');
            if (!form) return;
            const input = form.querySelector('[data-tag-note-edit-input]');
            if (input) input.value = input.defaultValue || '';
            form.hidden = true;
            item?.classList.remove('is-editing');
        });
    });

    tagNotesModal?.querySelectorAll('[data-tag-note-delete-form]').forEach(form => {
        form.addEventListener('submit', event => {
            if (!window.confirm('Usunąć tę notatkę?')) {
                event.preventDefault();
            }
        });
    });

    function readProjectInfoCell(row, column) {
        if (!row || !column) return '';
        return (row.querySelector(`[data-column="${column}"]`)?.textContent || '').replace(/\s+/g, ' ').trim();
    }

    function setProjectInfoText(element, value, fallback = 'Brak danych') {
        if (!element) return;
        element.textContent = value && value.trim() ? value.trim() : fallback;
    }

    function setProjectInfoProgress(value) {
        const label = value && value.trim() ? value.trim() : '0%';
        const normalizedValue = Number.parseFloat(label.replace(',', '.'));
        const progress = Number.isFinite(normalizedValue) ? Math.max(0, Math.min(100, normalizedValue)) : 0;

        setProjectInfoText(projectInfoProgressValue || projectInfoProgress, label, '0%');
        if (projectInfoProgressFill) {
            projectInfoProgressFill.style.setProperty('--tasks-project-info-progress', `${progress}%`);
        }
    }

    function setProjectInfoRowsVisible(visibleRows) {
        Object.entries(projectInfoRows).forEach(([key, row]) => {
            if (!row) return;
            row.hidden = !visibleRows.has(key);
        });
    }

    function openProjectInfoPanel(button) {
        if (!projectInfoModal) return;

        const isTagInfo = button.matches('[data-open-tag-info]');
        const isSectionInfo = button.matches('[data-open-section-info]');
        const row = button.closest(isTagInfo ? '.tasks-tag-sheet__row' : (isSectionInfo ? '.tasks-section-row' : '.tasks-project-row')) || button.closest('.tasks-directory-row');
        const isKanbanProject = !isTagInfo && !isSectionInfo && ((button.dataset.projectType || row?.dataset.projectType || '') === 'kanban-space');
        const data = isTagInfo
            ? {
                name: button.dataset.tagName || readProjectInfoCell(row, 'tag_name'),
                code: button.dataset.tagCode || readProjectInfoCell(row, 'tag_code'),
                description: button.dataset.tagDescription || readProjectInfoCell(row, 'description'),
                progress: '',
                tasks: button.dataset.tagTasksLabel || readProjectInfoCell(row, 'task_count'),
                tagCategory: button.dataset.tagCategoryLabel || readProjectInfoCell(row, 'tag_type'),
                tagVisual: button.dataset.tagVisualLabel || readProjectInfoCell(row, 'tag_visual'),
                tagScope: button.dataset.tagScopeLabel || readProjectInfoCell(row, 'scope'),
                tagOwner: button.dataset.tagOwnerLabel || readProjectInfoCell(row, 'owner'),
                tagUsage: button.dataset.tagUsageNotes || readProjectInfoCell(row, 'usage_notes'),
                tagAutomation: button.dataset.tagAutomationRules || readProjectInfoCell(row, 'automation'),
                tagRelated: button.dataset.tagRelatedTags || readProjectInfoCell(row, 'related_tags'),
                status: button.dataset.tagStatusLabel || readProjectInfoCell(row, 'status'),
                stage: '',
                health: '',
                company: '',
                responsible: '',
                priority: button.dataset.tagPriorityLabel || readProjectInfoCell(row, 'priority'),
                start: '',
                due: '',
                budget: '',
                source: '',
                created: button.dataset.tagCreatedLabel || readProjectInfoCell(row, 'created_at'),
                lastActivity: ''
            }
            : isSectionInfo
            ? {
                name: button.dataset.sectionTitle || readProjectInfoCell(row, 'section'),
                code: button.dataset.sectionCode || button.dataset.sectionProjectCode || readProjectInfoCell(row, 'project_code'),
                description: button.dataset.sectionDescription || readProjectInfoCell(row, 'description'),
                progress: button.dataset.sectionProgressLabel || readProjectInfoCell(row, 'progress'),
                tasks: button.dataset.sectionTasksLabel || readProjectInfoCell(row, 'tasks_count'),
                status: button.dataset.sectionStatusLabel || readProjectInfoCell(row, 'section_status'),
                stage: button.dataset.sectionKindLabel || readProjectInfoCell(row, 'section_kind'),
                health: '',
                company: button.dataset.sectionProjectNameLabel || readProjectInfoCell(row, 'project_name'),
                responsible: button.dataset.sectionOwnerLabel || readProjectInfoCell(row, 'default_assignee'),
                priority: button.dataset.sectionPriorityLabel || readProjectInfoCell(row, 'priority'),
                start: '',
                due: button.dataset.sectionDueLabel || readProjectInfoCell(row, 'due_at'),
                budget: button.dataset.sectionWipLabel || readProjectInfoCell(row, 'wip_limit'),
                source: '',
                created: button.dataset.sectionCreatedLabel || readProjectInfoCell(row, 'created_at'),
                lastActivity: button.dataset.sectionLastActivityLabel || readProjectInfoCell(row, 'last_activity')
            }
            : {
                name: button.dataset.projectName || row?.dataset.projectName || readProjectInfoCell(row, 'project'),
                code: button.dataset.projectCode || row?.dataset.projectCode || readProjectInfoCell(row, 'project_code'),
                description: button.dataset.projectDescription || row?.dataset.projectDescription || readProjectInfoCell(row, 'description'),
                progress: button.dataset.projectProgressLabel || readProjectInfoCell(row, 'progress'),
                tasks: button.dataset.projectTasksLabel || readProjectInfoCell(row, 'tasks_count'),
                status: button.dataset.projectStatusLabel || readProjectInfoCell(row, 'project_status'),
                stage: button.dataset.projectStageLabel || readProjectInfoCell(row, isKanbanProject ? 'sections_count' : 'stage'),
                health: button.dataset.projectHealthLabel || readProjectInfoCell(row, 'health'),
                company: button.dataset.projectCompanyLabel || readProjectInfoCell(row, 'company'),
                responsible: button.dataset.projectResponsibleLabel || readProjectInfoCell(row, 'responsible_user'),
                priority: button.dataset.projectPriorityLabel || readProjectInfoCell(row, 'priority'),
                start: button.dataset.projectStartLabel || readProjectInfoCell(row, 'start_at'),
                due: button.dataset.projectDueLabel || readProjectInfoCell(row, 'due_at'),
                budget: button.dataset.projectBudgetLabel || readProjectInfoCell(row, 'budget'),
                source: button.dataset.projectSourceLabel || readProjectInfoCell(row, 'source'),
                created: button.dataset.projectCreatedLabel || readProjectInfoCell(row, 'created_at'),
                lastActivity: button.dataset.projectLastActivityLabel || readProjectInfoCell(row, 'last_activity')
            };

        if (projectInfoTitle) projectInfoTitle.textContent = isTagInfo ? 'Informacje o tagu' : (isSectionInfo ? 'Informacje o grupie' : (isKanbanProject ? 'Informacje o przestrzeni' : 'Informacje o projekcie'));
        setProjectInfoRowsVisible(
            isTagInfo
                ? new Set(['code', 'tasks', 'tagCategory', 'tagVisual', 'tagScope', 'tagOwner', 'tagUsage', 'tagAutomation', 'tagRelated', 'status', 'priority', 'created'])
                : isSectionInfo
                    ? new Set(['code', 'progress', 'tasks', 'status', 'stage', 'responsible', 'priority', 'due', 'budget', 'created', 'lastActivity'])
                    : isKanbanProject
                        ? new Set(['code', 'progress', 'tasks', 'status', 'stage', 'responsible', 'priority', 'created', 'lastActivity'])
                        : new Set(['code', 'progress', 'tasks', 'status', 'stage', 'health', 'company', 'responsible', 'priority', 'start', 'due', 'budget', 'source', 'created', 'lastActivity'])
        );
        setProjectInfoText(projectInfoName, data.name, isTagInfo ? 'Tag' : (isSectionInfo ? 'Grupa' : (isKanbanProject ? 'Przestrzeń' : 'Projekt')));
        setProjectInfoText(projectInfoCode, data.code, isSectionInfo ? 'Brak kodu grupy' : 'Brak kodu');
        setProjectInfoText(projectInfoDescription, data.description, 'Brak opisu');
        setProjectInfoProgress(data.progress);
        setProjectInfoText(projectInfoTasks, data.tasks, '0/0');
        setProjectInfoText(projectInfoTagCategory, data.tagCategory, 'Brak typu');
        setProjectInfoText(projectInfoTagVisual, data.tagVisual, 'Brak danych');
        setProjectInfoText(projectInfoTagScope, data.tagScope, 'Brak zakresu');
        setProjectInfoText(projectInfoTagOwner, data.tagOwner, 'Brak właściciela');
        setProjectInfoText(projectInfoTagUsage, data.tagUsage, 'Brak opisu użycia');
        setProjectInfoText(projectInfoTagAutomation, data.tagAutomation, 'Brak reguł');
        setProjectInfoText(projectInfoTagRelated, data.tagRelated, 'Brak powiązań');
        setProjectInfoText(projectInfoStatus, data.status, 'Brak statusu');
        setProjectInfoText(projectInfoStage, data.stage, isSectionInfo ? 'Brak typu' : 'Brak etapu');
        setProjectInfoText(projectInfoHealth, data.health, 'Brak kondycji');
        setProjectInfoText(projectInfoCompany, data.company, isSectionInfo ? 'Brak projektu' : 'Brak firmy');
        setProjectInfoText(projectInfoResponsible, data.responsible, 'Brak osoby');
        setProjectInfoText(projectInfoPriority, data.priority, 'Brak');
        setProjectInfoText(projectInfoStart, data.start, 'Brak startu');
        setProjectInfoText(projectInfoDue, data.due, 'Brak terminu');
        setProjectInfoText(projectInfoBudget, data.budget, isSectionInfo ? 'Brak limitu' : 'Brak budżetu');
        setProjectInfoText(projectInfoSource, data.source, 'Brak źródła');
        setProjectInfoText(projectInfoCreated, data.created, 'Brak danych');
        setProjectInfoText(projectInfoLastActivity, data.lastActivity, 'Brak aktywności');

        closeProjectActionMenus();
        closeSectionActionMenu();
        closeStatusFilterMenu();
        closePriorityFilterMenu();
        closeDirectoryMembersMenus();
        closeInlineSelectDropdowns();
        openModal(projectInfoModal, projectInfoBody);
    }

    openProjectInfoButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.stopPropagation();
            openProjectInfoPanel(button);
        });
    });

    openSectionInfoButtons.forEach(button => {
        button.addEventListener('click', event => {
            event.stopPropagation();
            openProjectInfoPanel(button);
        });
    });

    openSectionCreateButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (sectionCreateProjectInput) sectionCreateProjectInput.value = button.dataset.projectId || '';
            if (sectionCreateProjectSelect) sectionCreateProjectSelect.value = button.dataset.projectId || '';
            if (sectionCreateTitleInput) sectionCreateTitleInput.value = '';
            if (sectionCreateDescriptionInput) sectionCreateDescriptionInput.value = '';
            setFieldValue(sectionCreateCodeInput, '');
            setFieldValue(sectionCreateKindInput, 'issues');
            setFieldValue(sectionCreateStatusInput, 'open');
            setFieldValue(sectionCreateOwnerInput, '');
            setFieldValue(sectionCreatePriorityInput, 'none');
            setFieldValue(sectionCreateDueAtInput, '');
            setFieldValue(sectionCreateWipLimitInput, '');
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
            if (issueBillableInput) issueBillableInput.checked = true;
            openModal(issueModal, issueTitleInput, updateIssueSubmitState);
        });
    });

    openContactButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (button.disabled) return;
            openModal(contactCreateModal, contactAncoreLoginInput || contactFirstNameInput);
        });
    });

    openCompanyButtons.forEach(button => {
        button.addEventListener('click', () => {
            if (button.disabled) return;
            openModal(companyCreateModal, companyNameInput);
        });
    });

    issueProjectPicker?.querySelector('[data-picker-toggle]')?.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = !issueProjectPicker.classList.contains('is-open');
        closeIssuePickers(issueProjectPicker);
        issueProjectPicker.classList.toggle('is-open', isOpen);
        this.setAttribute('aria-expanded', String(isOpen));
        if (isOpen) {
            hydrateIssuePickerOptions();
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
            hydrateIssuePickerOptions();
            resetPickerSearch(issueSectionPicker);
            setTimeout(() => issueSectionPicker.querySelector('[data-picker-search]')?.focus(), 30);
        }
    });

    issueProjectPicker?.addEventListener('click', function(e) {
        const option = e.target.closest('[data-project-option]');
        if (option && issueProjectPicker.contains(option)) {
            e.stopPropagation();
            selectIssueProject(option.dataset.projectId || '', option.dataset.defaultSectionId || '');
            closeIssuePickers();
        }
    });

    issueSectionPicker?.addEventListener('click', function(e) {
        const option = e.target.closest('[data-section-option]');
        if (option && issueSectionPicker.contains(option)) {
            e.stopPropagation();
            selectIssueProject(option.dataset.sectionProjectId || '', option.dataset.sectionId || '');
            closeIssuePickers();
        }
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

    issuePickerSearchButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation();
            const input = this.closest('.tasks-chip-picker__search')?.querySelector('[data-picker-search]');
            if (!input) return;
            filterPickerSearch(input);
            input.focus();
        });
    });

    document.querySelectorAll('[data-close-modal]').forEach(button => {
        button.addEventListener('click', function() {
            closeModal(this.closest('.tasks-modal'));
        });
    });

    window.addEventListener('resize', repositionOpenDirectorySharePermissionMenus, pageListenerOptions);
    document.addEventListener('scroll', repositionOpenDirectorySharePermissionMenus, pageCaptureListenerOptions);

    document.addEventListener('click', function(e) {
        if (createMenu && !createMenu.contains(e.target)) closeCreateMenu();
        if (!e.target.closest('[data-status-filter-menu]')) closeStatusFilterMenu();
        if (!e.target.closest('[data-priority-filter-menu]')) closePriorityFilterMenu();
        if (!e.target.closest('[data-project-filter-menu]')) closeProjectFilterMenus();
        if (!e.target.closest('[data-project-sort-menu]')) closeProjectSortMenu();
        if (!e.target.closest('[data-directory-members-menu]')) closeDirectoryMembersMenus();
        if (!e.target.closest('[data-section-actions]')) closeSectionActionMenu();
        if (!e.target.closest('[data-project-actions]')) closeProjectActionMenus();
        if (!e.target.closest('[data-issue-project-picker]') && !e.target.closest('[data-issue-section-picker]')) closeIssuePickers();
        if (!e.target.closest('[data-inline-select-dropdown]')) closeInlineSelectDropdowns();
        if (!e.target.closest('[data-project-page-size-dropdown]')) closeProjectPageSizeDropdown();
        if (!e.target.closest('[data-task-status-page-size-dropdown]')) closeTaskStatusPageSizeDropdowns();
        if (!e.target.closest('[data-company-select-dropdown]') && !e.target.closest('[data-company-select-menu]')) closeCompanySelectDropdowns();
        if (!e.target.closest('[data-responsible-select-dropdown]') && !e.target.closest('[data-responsible-select-menu]')) closeResponsibleSelectDropdowns();
        if (!e.target.closest('[data-directory-share-permission-picker]')) closeDirectorySharePermissionPickers();
        if (!e.target.closest('[data-contact-custom-select]')) closeContactCustomSelects();
        if (emojiPicker && !emojiPicker.contains(e.target) && !e.target.closest('[data-project-icon-picker]')) {
            closeEmojiPicker();
        }
    }, pageListenerOptions);

    if (projectNameInput) {
        projectNameInput.addEventListener('input', function() {
            updateProjectSubmitState();
        });
    }

    if (tagNameInput) {
        tagNameInput.addEventListener('input', updateTagSubmitState);
        updateTagSubmitState();
    }

    if (directorySharePersonInputs.length) {
        directorySharePersonInputs.forEach(input => {
            input.addEventListener('input', function() {
                syncDirectoryShareSelectedValuesFromInput(this);
                updateDirectoryShareSubmitState();
                syncDirectoryShareResults();
                if (this.value.trim()) {
                    setDirectoryShareContactsOpen(true);
                }
            });
        });
        updateDirectoryShareSubmitState();
        syncDirectoryShareResults();
    }

    directorySharePickOptions.forEach(option => {
        const checkbox = option.querySelector('[data-directory-share-check]');
        option.addEventListener('click', function(event) {
            if (event.target.closest('[data-directory-share-check]')) return;
            event.preventDefault();
            toggleDirectorySharePickOption(this);
        });
        option.addEventListener('keydown', function(event) {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            event.preventDefault();
            this.click();
        });
        checkbox?.addEventListener('click', function(event) {
            event.stopPropagation();
        });
        checkbox?.addEventListener('change', function() {
            toggleDirectorySharePickOptionFromCheckbox(option, this);
        });
    });

    directoryShareLinkCreateBtn?.addEventListener('click', createDirectoryShareLink);
    directoryShareLinkCopyBtn?.addEventListener('click', copyDirectoryShareLink);
    directoryShareLinkRevokeBtn?.addEventListener('click', revokeDirectoryShareLink);

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

    if (contactAncoreLoginInput) {
        contactAncoreLoginInput.addEventListener('input', () => {
            window.clearTimeout(contactAncoreLoginTimer);
            contactAncoreLoginTimer = window.setTimeout(lookupContactAncoreLogin, 280);
        });
        contactAncoreLoginInput.addEventListener('blur', lookupContactAncoreLogin);
        if (contactAncoreLoginInput.value.trim()) {
            lookupContactAncoreLogin();
        }
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
    if (sectionCreateProjectSelect) {
        sectionCreateProjectSelect.addEventListener('change', updateSectionCreateSubmitState);
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
            if (modal.id === 'contact-create-modal') {
                focusTarget = contactAncoreLoginInput || contactFirstNameInput;
                onOpen = null;
            }
            if (modal.id === 'company-create-modal') {
                focusTarget = companyNameInput;
                onOpen = null;
            }
            openModal(modal, focusTarget, onOpen);
        }
    });

    document.addEventListener('keydown', function(e) {
        if (handleContactCustomSelectKeydown(e)) return;

        if (e.key === 'Escape') {
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeIssuePickers();
            closeProjectPageSizeDropdown();
            closeContactCustomSelects();
            closeEmojiPicker();
            const openModalEl = document.querySelector('.tasks-modal.is-open');
            if (openModalEl) closeModal(openModalEl);
        }
    }, pageListenerOptions);

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

    const ignoredDirectoryRowClickColumns = new Set(['select', 'action', 'info']);

    function getDirectoryRowColumnBounds(row, column) {
        if (!row) return null;
        const cells = Array.from(row.children).filter(child => child.dataset?.column);
        const index = cells.findIndex(child => child.dataset.column === column);
        if (index === -1) return null;

        const rowRect = row.getBoundingClientRect();
        const cellRect = cells[index].getBoundingClientRect();
        const nextCellRect = cells[index + 1]?.getBoundingClientRect();

        return {
            left: index === 0 ? rowRect.left : cellRect.left,
            right: nextCellRect ? nextCellRect.left : cellRect.right
        };
    }

    function isIgnoredDirectoryColumnClick(event, row) {
        if (!row || typeof event.clientX !== 'number') return false;

        return Array.from(ignoredDirectoryRowClickColumns).some(column => {
            const bounds = getDirectoryRowColumnBounds(row, column);
            return bounds && event.clientX >= bounds.left && event.clientX < bounds.right;
        });
    }

    function isDirectoryColumnClick(event, row, column) {
        if (!row || typeof event.clientX !== 'number') return false;

        const bounds = getDirectoryRowColumnBounds(row, column);
        return Boolean(bounds && event.clientX >= bounds.left && event.clientX < bounds.right);
    }

    function getDirectoryRowSelectCheckbox(row) {
        return row?.querySelector(':scope > .tasks-row-checkbox[data-column="select"]') || null;
    }

    function toggleDirectoryRowCheckboxFromSelectColumn(event, row) {
        if (!isDirectoryColumnClick(event, row, 'select')) return false;
        if (event.target.type === 'checkbox' || event.target.closest('a, input, button, select, textarea')) {
            return false;
        }

        const checkbox = getDirectoryRowSelectCheckbox(row);
        if (!checkbox || checkbox.disabled) return false;

        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
        event.preventDefault();
        event.stopPropagation();
        return true;
    }

    function shouldIgnoreRowClick(event, row = null) {
        const cell = event.target.closest('td');
        const directoryCell = event.target.closest('[data-column]');
        const form = event.target.closest('form');
        const rowForm = row ? row.closest('form') : null;

        return event.target.type === 'checkbox'
            || (form && form !== rowForm)
            || ignoredDirectoryRowClickColumns.has(directoryCell?.dataset.column)
            || isIgnoredDirectoryColumnClick(event, row)
            || event.target.closest('a, input, button, select, textarea')
            || (cell && cell.querySelector('.task-checkbox'));
    }

    function isReadonlyTaskRow(row) {
        return row?.dataset.readonly === 'true' || row?.getAttribute('draggable') === 'false';
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
                navigateWithinApp(viewUrl);
            }
        });

        row.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            if (shouldIgnoreRowClick(e, this)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (!viewUrl) return;
            e.preventDefault();
            rememberTaskReturnPoint(viewUrl);
            navigateWithinApp(viewUrl);
        });
    });

    [...projectRows, ...sectionRows, ...contactsDirectoryRows].forEach(row => {
        row.addEventListener('click', function(e) {
            if (toggleDirectoryRowCheckboxFromSelectColumn(e, this)) return;
            if (shouldIgnoreRowClick(e, this)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (viewUrl) navigateWithinApp(viewUrl);
        });

        row.addEventListener('keydown', function(e) {
            if (e.key !== 'Enter' && e.key !== ' ') return;
            if (shouldIgnoreRowClick(e, this)) return;
            const viewUrl = this.getAttribute('data-view-url');
            if (!viewUrl) return;
            e.preventDefault();
            navigateWithinApp(viewUrl);
        });
    });

    document.querySelectorAll('.tasks-directory-header > [data-column="select"], .contacts-directory-header > [data-column="select"]').forEach(selectCell => {
        selectCell.addEventListener('click', function(e) {
            if (e.target.type === 'checkbox' || e.target.closest('input, button, a, select, textarea')) return;

            const checkbox = this.querySelector('input[type="checkbox"]');
            if (!checkbox || checkbox.disabled) return;

            checkbox.checked = !checkbox.checked;
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            e.preventDefault();
            e.stopPropagation();
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
        if (isReadonlyTaskRow(row)) return;

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
            if (isReadonlyTaskRow(this)) {
                event.preventDefault();
                return;
            }
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
            if (isReadonlyTaskRow(row)) return;
            moveTaskRow(row, this);
        });
    });

    // Checkbox functionality
    function getSelectedTaskCheckboxes() {
        return Array.from(document.querySelectorAll('.task-checkbox:checked'))
            .filter(cb => cb.id !== 'select-all-checkbox');
    }

    function getSelectedSectionCheckboxes() {
        return Array.from(sectionCheckboxes).filter(cb => cb.checked);
    }

    function getSelectedSectionCheckbox() {
        const selected = getSelectedSectionCheckboxes();
        return selected.length === 1 ? selected[0] : null;
    }

    function getSelectedProjectCheckboxes() {
        return Array.from(projectCheckboxes).filter(cb => cb.checked);
    }

    function getSelectedProjectCheckbox() {
        const selected = getSelectedProjectCheckboxes();
        return selected.length === 1 ? selected[0] : null;
    }

    function getSelectedTagCheckboxes() {
        return Array.from(tagCheckboxes).filter(cb => cb.checked);
    }

    function getSelectedTagCheckbox() {
        const selected = getSelectedTagCheckboxes();
        return selected.length === 1 ? selected[0] : null;
    }

    function rowIsShown(row) {
        return row && row.style.display !== 'none';
    }

    function checkboxRow(checkbox) {
        return checkbox.closest('.task-row, .tasks-project-row, .tasks-section-row, .tasks-all-groups-row, .contacts-directory-row');
    }

    function taskCheckboxCanEdit(checkbox) {
        if (!checkbox) return false;
        const row = checkboxRow(checkbox);
        if (row && isReadonlyTaskRow(row)) return false;
        return checkbox.dataset.canEdit !== 'false';
    }

    function checkboxCanManage(checkbox) {
        return Boolean(checkbox) && checkbox.dataset.canManage !== 'false';
    }

    function allCheckboxesCanManage(selectedCheckboxes) {
        return selectedCheckboxes.length > 0 && selectedCheckboxes.every(checkboxCanManage);
    }

    function getSelectAllTargetCheckboxes(visibleOnly = false) {
        const target = selectAllCheckbox?.dataset.selectAllTarget || '';
        let targetCheckboxes = [];

        if (target === 'projects') {
            targetCheckboxes = Array.from(projectCheckboxes);
        } else if (target === 'sections') {
            targetCheckboxes = Array.from(sectionCheckboxes);
        } else if (target === 'tags') {
            targetCheckboxes = Array.from(tagCheckboxes);
        } else if (target === 'contacts') {
            targetCheckboxes = Array.from(contactCheckboxes);
        } else if (target === 'companies') {
            targetCheckboxes = Array.from(companyCheckboxes);
        } else {
            targetCheckboxes = Array.from(checkboxes).filter(cb => cb.id !== 'select-all-checkbox');
        }

        targetCheckboxes = targetCheckboxes.filter(cb => !cb.disabled);

        if (!visibleOnly) return targetCheckboxes;

        return targetCheckboxes.filter(cb => rowIsShown(checkboxRow(cb)));
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
        const selectedTaskCheckbox = selectedTaskCheckboxes.length === 1 ? selectedTaskCheckboxes[0] : null;
        setMenuButtonState(
            editSelectedTaskMenuBtn,
            selectedTaskCheckboxes.length === 1 && taskCheckboxCanEdit(selectedTaskCheckbox),
            { taskId: selectedTaskCheckbox?.dataset.taskId || '' }
        );
        setMenuButtonState(
            deleteSelectedTaskMenuBtn,
            allCheckboxesCanManage(selectedTaskCheckboxes),
            { taskCount: String(selectedTaskCheckboxes.length) }
        );

        const selectedSectionCheckboxes = getSelectedSectionCheckboxes();
        const selectedSectionCheckbox = selectedSectionCheckboxes.length === 1 ? selectedSectionCheckboxes[0] : null;
        const sectionDataset = {
            sectionId: selectedSectionCheckbox?.dataset.sectionId || '',
            sectionTitle: selectedSectionCheckbox?.dataset.sectionTitle || '',
            sectionDescription: selectedSectionCheckbox?.dataset.sectionDescription || '',
            sectionIcon: selectedSectionCheckbox?.dataset.sectionIcon || ''
        };
        setMenuButtonState(editSelectedSectionMenuBtn, selectedSectionCheckboxes.length === 1 && checkboxCanManage(selectedSectionCheckbox), sectionDataset);
        setMenuButtonState(
            infoSelectedSectionMenuBtn,
            selectedSectionCheckboxes.length === 1,
            sectionDataset
        );
        setMenuButtonState(
            notesSelectedSectionMenuBtn,
            selectedSectionCheckboxes.length === 1,
            sectionDataset
        );
        setMenuButtonState(
            deleteSelectedSectionMenuBtn,
            allCheckboxesCanManage(selectedSectionCheckboxes),
            sectionDataset
        );

        const selectedProjectCheckboxes = getSelectedProjectCheckboxes();
        const selectedProjectCheckbox = selectedProjectCheckboxes.length === 1 ? selectedProjectCheckboxes[0] : null;
        const projectDataset = {
            projectId: selectedProjectCheckbox?.dataset.projectId || '',
            projectName: selectedProjectCheckbox?.dataset.projectName || '',
            projectDescription: selectedProjectCheckbox?.dataset.projectDescription || '',
            projectCode: selectedProjectCheckbox?.dataset.projectCode || '',
            projectIcon: selectedProjectCheckbox?.dataset.projectIcon || '',
            projectPriority: selectedProjectCheckbox?.dataset.projectPriority || 'none',
            projectDueAt: selectedProjectCheckbox?.dataset.projectDueAt || ''
        };
        setMenuButtonState(
            editSelectedProjectMenuBtn,
            selectedProjectCheckboxes.length === 1 && checkboxCanManage(selectedProjectCheckbox),
            projectDataset
        );
        setMenuButtonState(
            editSelectedProjectBarBtn,
            selectedProjectCheckboxes.length === 1 && checkboxCanManage(selectedProjectCheckbox),
            projectDataset
        );
        setMenuButtonState(
            infoSelectedProjectMenuBtn,
            selectedProjectCheckboxes.length === 1,
            projectDataset
        );
        setMenuButtonState(
            notesSelectedProjectMenuBtn,
            selectedProjectCheckboxes.length === 1,
            projectDataset
        );
        setMenuButtonState(
            deleteSelectedProjectMenuBtn,
            allCheckboxesCanManage(selectedProjectCheckboxes),
            projectDataset
        );

        const selectedTagCheckboxes = getSelectedTagCheckboxes();
        const selectedTagCheckbox = selectedTagCheckboxes.length === 1 ? selectedTagCheckboxes[0] : null;
        const tagDataset = {
            tagId: selectedTagCheckbox?.dataset.tagId || '',
            tagName: selectedTagCheckbox?.dataset.tagName || '',
            tagDescription: selectedTagCheckbox?.dataset.tagDescription || '',
            tagCategory: selectedTagCheckbox?.dataset.tagCategory || '',
            tagColor: selectedTagCheckbox?.dataset.tagColor || '',
            tagIcon: selectedTagCheckbox?.dataset.tagIcon || '',
            tagPriority: selectedTagCheckbox?.dataset.tagPriority || '',
            tagScope: selectedTagCheckbox?.dataset.tagScope || '',
            tagOwnerLabel: selectedTagCheckbox?.dataset.tagOwnerLabel || '',
            tagStatus: selectedTagCheckbox?.dataset.tagStatus || '',
            tagUsageNotes: selectedTagCheckbox?.dataset.tagUsageNotes || '',
            tagAutomationRules: selectedTagCheckbox?.dataset.tagAutomationRules || '',
            tagRelatedTags: selectedTagCheckbox?.dataset.tagRelatedTags || '',
            tagCount: String(selectedTagCheckboxes.length)
        };
        setMenuButtonState(editSelectedTagMenuBtn, selectedTagCheckboxes.length === 1, tagDataset);
        setMenuButtonState(
            deleteSelectedTagMenuBtn,
            selectedTagCheckboxes.length > 0,
            tagDataset
        );
    }

    function updateSelection() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        const editableTaskCheckboxes = selectedTaskCheckboxes.filter(taskCheckboxCanEdit);
        const allSelectedTasksEditable = selectedTaskCheckboxes.length > 0 && editableTaskCheckboxes.length === selectedTaskCheckboxes.length;
        const allSelectedTasksManageable = allCheckboxesCanManage(selectedTaskCheckboxes);
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
                    const canEditSelectedTask = count === 1 && taskCheckboxCanEdit(selectedTaskCheckboxes[0]);
                    editBtn.classList.toggle('u-hidden', !canEditSelectedTask);
                    editBtn.disabled = !canEditSelectedTask;
                }

                if (deleteBtn) {
                    deleteBtn.disabled = !allSelectedTasksManageable;
                }

                // Update Status Toggle Button
                if (statusToggleBtn) {
                    statusToggleBtn.disabled = !allSelectedTasksEditable;
                    const statuses = Array.from(editableTaskCheckboxes).map(cb => cb.closest('.task-row').dataset.status);
                    const anyOpen = statuses.some(s => s !== 'closed');
                    
                    if (anyOpen) {
                        statusToggleBtn.className = 'btn btn-secondary tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            ${window.AncoreIcons ? window.AncoreIcons.html('circle-check') : '<i data-lucide="circle-check" aria-hidden="true"></i>'}
                            ${taskCopy.closeOne}
                        `;
                        statusToggleBtn.dataset.targetStatus = 'closed';
                    } else {
                        statusToggleBtn.className = 'btn btn-secondary tasks-toolbar-btn';
                        statusToggleBtn.innerHTML = `
                            ${window.AncoreIcons ? window.AncoreIcons.html('rotate-ccw') : '<i data-lucide="rotate-ccw" aria-hidden="true"></i>'}
                            Otwórz ponownie
                        `;
                        statusToggleBtn.dataset.targetStatus = 'reopened';
                    }
                    renderLucideIcons(statusToggleBtn);
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
            const projectContainer = cb.closest('.tasks-project-row, .tasks-project-board-group');
            projectContainer?.classList.toggle('checked', cb.checked);
        });

        tagCheckboxes.forEach(cb => {
            cb.closest('.tasks-all-groups-row, .tasks-tag-sheet__row')?.classList.toggle('checked', cb.checked);
        });

        contactCheckboxes.forEach(cb => {
            cb.closest('.contacts-directory-row')?.classList.toggle('checked', cb.checked);
        });

        companyCheckboxes.forEach(cb => {
            cb.closest('.contacts-directory-row')?.classList.toggle('checked', cb.checked);
        });

        // Update select all state
        if (selectAllCheckbox) {
            const targetCheckboxes = getSelectAllTargetCheckboxes(true);
            const selectedTargetCheckboxes = targetCheckboxes.filter(cb => cb.checked);
            selectAllCheckbox.checked = targetCheckboxes.length > 0 && selectedTargetCheckboxes.length === targetCheckboxes.length;
            selectAllCheckbox.indeterminate = selectedTargetCheckboxes.length > 0 && selectedTargetCheckboxes.length < targetCheckboxes.length;
            selectAllCheckbox.disabled = targetCheckboxes.length === 0;
        }
    }

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            getSelectAllTargetCheckboxes(true).forEach(cb => {
                cb.checked = this.checked;
            });
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
            updateSelection();
        });
    });

    projectCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            updateSelection();
        });
    });

    tagCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            updateSelection();
        });
    });

    contactCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
            updateSelection();
        });
    });

    companyCheckboxes.forEach(cb => {
        cb.addEventListener('change', function(e) {
            e.stopPropagation();
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
            const values = Array.isArray(value) ? value : [value];
            values.forEach(item => {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = name;
                input.value = item;
                form.appendChild(input);
            });
        });

        document.body.appendChild(form);
        form.submit();
    }

    function postDeleteSection(sectionIds) {
        const ids = Array.isArray(sectionIds) ? sectionIds : [sectionIds];
        postPageAction('delete_section', { section_ids: ids });
    }

    function postDeleteProject(projectIds) {
        const ids = Array.isArray(projectIds) ? projectIds : [projectIds];
        postPageAction('delete_project', { project_ids: ids });
    }

    function postDeleteTag(tagIds) {
        const ids = Array.isArray(tagIds) ? tagIds : [tagIds];
        postPageAction('delete_tag', {
            tag_id: ids[0] || '',
            tag_ids: ids
        });
    }

    function editSelectedTask() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        if (selectedTaskCheckboxes.length !== 1) return;
        if (!taskCheckboxCanEdit(selectedTaskCheckboxes[0])) return;

        const row = checkboxRow(selectedTaskCheckboxes[0]);
        const viewUrl = row?.getAttribute('data-view-url');
        if (viewUrl) {
            rememberTaskReturnPoint(viewUrl);
            navigateWithinApp(viewUrl);
            return;
        }

        const taskId = selectedTaskCheckboxes[0].dataset.taskId;
        if (taskId) navigateWithinApp(`/${taskAppSegment}/view-task/${taskId}/`);
    }

    function openSectionRenameFromDataset(sectionDataset) {
        if (!sectionDataset || !sectionRenameModal) return;
        if (sectionDataset.canManage === 'false') return;

        setFieldValue(sectionRenameIdInput, sectionDataset.sectionId);
        setFieldValue(sectionRenameTitleInput, sectionDataset.sectionTitle);
        setFieldValue(sectionRenameDescriptionInput, sectionDataset.sectionDescription);
        setFieldValue(sectionRenameCodeInput, sectionDataset.sectionCode);
        setFieldValue(sectionRenameKindInput, sectionDataset.sectionKind || 'issues');
        setFieldValue(sectionRenameStatusInput, sectionDataset.sectionStatus || 'open');
        setFieldValue(sectionRenameOwnerInput, sectionDataset.sectionOwnerId);
        setFieldValue(sectionRenamePriorityInput, sectionDataset.sectionPriority || 'none');
        syncInlineSelectForSelect(sectionRenamePriorityInput);
        setFieldValue(sectionRenameDueAtInput, sectionDataset.sectionDueAt);
        setFieldValue(sectionRenameWipLimitInput, sectionDataset.sectionWipLimit);
        setFieldValue(sectionRenameIconInput, sectionDataset.sectionIcon);
        syncProjectIconPickers();
        closeSectionActionMenu();
        openModal(sectionRenameModal, sectionRenameTitleInput, updateSectionRenameSubmitState);
        setTimeout(() => sectionRenameTitleInput?.select(), 60);
    }

    function editSelectedSection() {
        const selectedSectionCheckbox = getSelectedSectionCheckbox();
        if (!selectedSectionCheckbox || !checkboxCanManage(selectedSectionCheckbox)) return;
        openSectionRenameFromDataset(selectedSectionCheckbox.dataset);
    }

    function openSelectedSectionInfo() {
        const selectedSectionCheckbox = getSelectedSectionCheckbox();
        if (!selectedSectionCheckbox) return;

        const row = checkboxRow(selectedSectionCheckbox);
        const infoButton = row?.querySelector('[data-open-section-info]');
        if (!infoButton) return;

        openProjectInfoPanel(infoButton);
    }

    function openSelectedSectionNotes() {
        const selectedSectionCheckbox = getSelectedSectionCheckbox();
        if (!selectedSectionCheckbox) return;

        const row = checkboxRow(selectedSectionCheckbox);
        closeSectionActionMenu();
        openSectionNotesModal(row?.querySelector('[data-open-section-notes]') || selectedSectionCheckbox);
    }

    function editSelectedProject() {
        const selectedProjectCheckbox = getSelectedProjectCheckbox();
        if (!selectedProjectCheckbox || !projectRenameModal) return;
        if (!checkboxCanManage(selectedProjectCheckbox)) return;

        setProjectRenameFieldsFromDataset(selectedProjectCheckbox.dataset);
        syncProjectIconPickers();
        closeSectionActionMenu();
        openModal(projectRenameModal, projectRenameNameInput, updateProjectRenameSubmitState);
        setTimeout(() => projectRenameNameInput?.select(), 60);
    }

    function openSelectedProjectInfo() {
        const selectedProjectCheckbox = getSelectedProjectCheckbox();
        if (!selectedProjectCheckbox) return;

        openProjectInfoPanel(selectedProjectCheckbox);
    }

    function openSelectedProjectNotes() {
        const selectedProjectCheckbox = getSelectedProjectCheckbox();
        if (!selectedProjectCheckbox) return;

        closeSectionActionMenu();
        openProjectNotesModal(selectedProjectCheckbox);
    }

    function openTagEditFromDataset(tagDataset) {
        if (!tagDataset || !tagModal) return;

        closeSectionActionMenu();
        setTagModalMode('edit', {
            tagId: tagDataset.tagId || '',
            tagName: tagDataset.tagName || '',
            tagDescription: tagDataset.tagDescription || '',
            tagCategory: tagDataset.tagCategory || '',
            tagColor: tagDataset.tagColor || '',
            tagIcon: tagDataset.tagIcon || '',
            tagPriority: tagDataset.tagPriority || '',
            tagScope: tagDataset.tagScope || '',
            tagOwnerLabel: tagDataset.tagOwnerLabel || '',
            tagStatus: tagDataset.tagStatus || '',
            tagUsageNotes: tagDataset.tagUsageNotes || '',
            tagAutomationRules: tagDataset.tagAutomationRules || '',
            tagRelatedTags: tagDataset.tagRelatedTags || ''
        });
        openModal(tagModal, tagNameInput, updateTagSubmitState);
        setTimeout(() => tagNameInput?.select(), 60);
    }

    function editSelectedTag() {
        const selectedTagCheckbox = getSelectedTagCheckbox();
        if (!selectedTagCheckbox || !tagModal) return;
        openTagEditFromDataset(selectedTagCheckbox.dataset);
    }

    function deleteSelectedSection() {
        const selectedSectionCheckboxes = getSelectedSectionCheckboxes();
        if (!allCheckboxesCanManage(selectedSectionCheckboxes)) return;
        const sectionIds = selectedSectionCheckboxes.map(cb => cb.dataset.sectionId).filter(Boolean);
        if (!sectionIds.length) return;

        const isBulk = sectionIds.length > 1;
        const sectionTitle = escapeHtml(selectedSectionCheckboxes[0]?.dataset.sectionTitle || sectionCopy.deleteFallback);

        closeSectionActionMenu();
        window.showConfirmModal({
            title: isBulk ? 'Usuń grupy' : sectionCopy.deleteTitle,
            message: isBulk
                ? `Czy na pewno chcesz usunąć ${sectionIds.length} zaznaczone grupy? Zostaną usunięte razem z zadaniami.`
                : sectionCopy.deleteMessageTemplate.replace('{title}', sectionTitle),
            confirmText: isBulk ? 'Usuń grupy' : sectionCopy.deleteConfirm,
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => postDeleteSection(sectionIds)
        });
    }

    function deleteSelectedProject() {
        const selectedProjectCheckboxes = getSelectedProjectCheckboxes();
        if (!allCheckboxesCanManage(selectedProjectCheckboxes)) return;
        const projectIds = selectedProjectCheckboxes.map(cb => cb.dataset.projectId).filter(Boolean);
        if (!projectIds.length) return;

        const isBulk = projectIds.length > 1;
        const projectName = escapeHtml(selectedProjectCheckboxes[0]?.dataset.projectName || 'tę przestrzeń roboczą');

        closeSectionActionMenu();
        window.showConfirmModal({
            title: isBulk ? 'Usuń projekty' : 'Usuń przestrzeń roboczą',
            message: isBulk
                ? `Czy na pewno chcesz usunąć ${projectIds.length} zaznaczone projekty? Zostaną usunięte razem z grupami i zadaniami.`
                : `Czy na pewno chcesz usunąć przestrzeń roboczą „${projectName}”? ${taskCopy.projectDeleteNote}`,
            confirmText: isBulk ? 'Usuń projekty' : 'Usuń przestrzeń',
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => postDeleteProject(projectIds)
        });
    }

    function deleteSelectedTag() {
        const selectedTagCheckboxes = getSelectedTagCheckboxes();
        const tagIds = selectedTagCheckboxes.map(cb => cb.dataset.tagId).filter(Boolean);
        if (!tagIds.length) return;

        const isBulk = tagIds.length > 1;
        const tagName = escapeHtml(selectedTagCheckboxes[0]?.dataset.tagName || 'ten tag');

        closeSectionActionMenu();
        window.showConfirmModal({
            title: isBulk ? 'Usuń tagi' : 'Usuń tag',
            message: isBulk
                ? `Czy na pewno chcesz usunąć zaznaczone tagi (${tagIds.length})? Zostaną odpięte od ${taskCopy.itemPluralGen}.`
                : `Czy na pewno chcesz usunąć tag „${tagName}”? ${taskCopy.tagDetachNote}`,
            confirmText: isBulk ? 'Usuń tagi' : 'Usuń tag',
            cancelText: 'Anuluj',
            confirmClass: 'btn-danger',
            onConfirm: () => postDeleteTag(tagIds)
        });
    }

    function deleteSelectedTasks() {
        const selectedTaskCheckboxes = getSelectedTaskCheckboxes();
        if (!allCheckboxesCanManage(selectedTaskCheckboxes)) return;
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
            const selectedCheckboxes = getSelectedTaskCheckboxes();
            if (!selectedCheckboxes.length || selectedCheckboxes.some(cb => !taskCheckboxCanEdit(cb))) return;
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

    if (infoSelectedSectionMenuBtn) {
        infoSelectedSectionMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            openSelectedSectionInfo();
        });
    }

    if (notesSelectedSectionMenuBtn) {
        notesSelectedSectionMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            openSelectedSectionNotes();
        });
    }

    openSectionRenameButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            openSectionRenameFromDataset(this.dataset);
        });
    });

    if (editSelectedProjectMenuBtn) {
        editSelectedProjectMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedProject();
        });
    }

    if (editSelectedProjectBarBtn) {
        editSelectedProjectBarBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedProject();
        });
    }

    if (infoSelectedProjectMenuBtn) {
        infoSelectedProjectMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            openSelectedProjectInfo();
        });
    }

    if (notesSelectedProjectMenuBtn) {
        notesSelectedProjectMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            openSelectedProjectNotes();
        });
    }

    if (editSelectedTagMenuBtn) {
        editSelectedTagMenuBtn.addEventListener('click', function(e) {
            e.preventDefault();
            if (this.disabled) return;
            editSelectedTag();
        });
    }

    openTagEditButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            openTagEditFromDataset(this.dataset);
        });
    });

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

    function currentContactRows() {
        return document.querySelectorAll('.contacts-directory-row');
    }

    function getProjectPageSize() {
        const value = Number.parseInt(projectPageSizeSelect?.value || '', 10);
        return projectPageSizes.includes(value) ? value : projectPageSizes[0];
    }

    function syncProjectPageSizeDropdown() {
        if (!projectPageSizeSelect) return;

        const currentValue = String(getProjectPageSize());
        projectPageSizeSelect.value = currentValue;
        if (projectPageSizeLabel) {
            projectPageSizeLabel.textContent = currentValue;
        }
        projectPageSizeOptions.forEach(button => {
            const isActive = button.dataset.projectPageSizeValue === currentValue;
            button.classList.toggle('is-active', isActive);
            button.setAttribute('aria-checked', String(isActive));
        });
    }

    function filteredProjectRows() {
        return Array.from(currentProjectRows()).filter(row => row.dataset.projectFilterVisible !== 'false');
    }

    function setProjectRowVisibility(row, isVisible) {
        row.dataset.projectPaginationHidden = isVisible ? 'false' : 'true';
        row.style.display = isVisible ? '' : 'none';
    }

    function getProjectPaginationItems(totalPages) {
        const maxVisiblePages = 6;

        if (totalPages <= maxVisiblePages) {
            return Array.from({ length: totalPages }, (_, index) => index + 1);
        }

        const halfWindow = Math.floor(maxVisiblePages / 2);
        const maxStartPage = totalPages - maxVisiblePages + 1;
        const startPage = Math.min(
            Math.max(projectPaginationPage - halfWindow, 1),
            maxStartPage
        );

        return Array.from({ length: maxVisiblePages }, (_, index) => startPage + index);
    }

    function renderProjectPagination(totalPages) {
        if (!projectPaginationPages) return;

        projectPaginationPages.replaceChildren();

        getProjectPaginationItems(totalPages).forEach(item => {
            if (item === 'ellipsis') {
                const ellipsis = document.createElement('span');
                ellipsis.className = 'tasks-project-pagination__ellipsis';
                ellipsis.setAttribute('aria-hidden', 'true');
                ellipsis.textContent = '...';
                projectPaginationPages.appendChild(ellipsis);
                return;
            }

            const button = document.createElement('button');
            button.type = 'button';
            button.className = `tasks-project-pagination__button${item === projectPaginationPage ? ' is-active' : ''}`;
            button.textContent = String(item);
            button.dataset.projectPage = String(item);
            button.setAttribute('aria-label', `Strona ${item}`);
            if (item === projectPaginationPage) {
                button.setAttribute('aria-current', 'page');
            }
            projectPaginationPages.appendChild(button);
        });
    }

    function applyProjectPagination({ resetPage = false } = {}) {
        if (!projectPagination || !projectPageSizeSelect) return;
        if (usesServerProjectPagination) {
            projectPagination.hidden = false;
            return;
        }

        const rows = Array.from(currentProjectRows());
        if (!rows.length) {
            projectPagination.hidden = true;
            return;
        }

        if (resetPage) {
            projectPaginationPage = 1;
        }

        const visibleRows = filteredProjectRows();
        const pageSize = getProjectPageSize();
        const totalPages = Math.max(1, Math.ceil(visibleRows.length / pageSize));
        projectPaginationPage = Math.min(Math.max(projectPaginationPage, 1), totalPages);

        const firstIndex = (projectPaginationPage - 1) * pageSize;
        const lastIndex = firstIndex + pageSize;
        const visibleRowSet = new Set(visibleRows.slice(firstIndex, lastIndex));

        rows.forEach(row => {
            if (row.dataset.projectFilterVisible === 'false') {
                row.dataset.projectPaginationHidden = 'false';
                row.style.display = 'none';
                return;
            }
            setProjectRowVisibility(row, visibleRowSet.has(row));
        });

        if (projectPaginationSummary) {
            if (!visibleRows.length) {
                projectPaginationSummary.textContent = 'Brak projektów';
            } else {
                const firstVisible = firstIndex + 1;
                const lastVisible = Math.min(lastIndex, visibleRows.length);
                projectPaginationSummary.textContent = `${firstVisible}-${lastVisible} z ${visibleRows.length}`;
            }
        }

        renderProjectPagination(totalPages);

        if (projectPagePrev) {
            projectPagePrev.disabled = projectPaginationPage <= 1 || visibleRows.length === 0;
        }
        if (projectPageNext) {
            projectPageNext.disabled = projectPaginationPage >= totalPages || visibleRows.length === 0;
        }

        projectPagination.hidden = false;
    }

    function setProjectPaginationPage(page) {
        projectPaginationPage = page;
        applyProjectPagination();
        updateGroupVisibility();
        updateSelection();
    }

    window.ancoreRefreshProjectPagination = function({ resetPage = false } = {}) {
        applyProjectPagination({ resetPage });
        updateGroupVisibility();
        updateSelection();
    };

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
            const visibleRows = Array.from(group.querySelectorAll('.task-row, .tasks-project-row, .tasks-section-row, .contacts-directory-row')).filter(row => row.style.display !== 'none');
            group.style.display = visibleRows.length ? '' : 'none';
        });

        const activeSearch = document.getElementById('filter-search');
        const searchVal = normalizeFilterText(activeSearch ? activeSearch.value : '');

        document.querySelectorAll('.tasks-issue-group').forEach(group => {
            const visibleRows = Array.from(group.querySelectorAll('.task-row, .tasks-project-row, .tasks-section-row, .contacts-directory-row')).filter(row => row.style.display !== 'none');
            const hasEmptyState = group.querySelector('.tasks-empty-section, .tasks-empty-state') !== null;
            const groupMatchesSearch = rowMatchesSearch(group, searchVal);
            const isEmptyDirectoryBoard = group.closest('.tasks-project-board--empty, .tasks-group-board--empty, .tasks-tag-board--empty') !== null;
            group.style.display = (isEmptyDirectoryBoard || visibleRows.length || (hasEmptyState && groupMatchesSearch)) ? '' : 'none';
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

        statusFilterToggle?.classList.toggle('is-active', Boolean(statusVal));
        priorityFilterToggle?.classList.toggle('is-active', Boolean(priorityVal));
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
            const rowPriority = row.getAttribute('data-project-priority');
            const matchesPriority = !priorityVal || rowPriority === priorityVal;
            const isVisible = matchesPriority && matchesSearch;
            row.dataset.projectFilterVisible = isVisible ? 'true' : 'false';
            row.dataset.projectPaginationHidden = 'false';
            row.style.display = isVisible ? '' : 'none';
        });

        currentSectionRows().forEach(row => {
            const matchesSearch = rowMatchesSearch(row, searchVal);
            row.style.display = matchesSearch ? '' : 'none';
        });

        currentContactRows().forEach(row => {
            const matchesSearch = rowMatchesSearch(row, searchVal);
            row.style.display = matchesSearch ? '' : 'none';
        });

        applyProjectPagination({ resetPage: true });
        updateGroupVisibility();
        setActiveFilterButtons();
        updateSelection();
    }

    function getProjectFilterInput(param) {
        if (!param) return null;
        return document.querySelector(`[data-project-filter-input="${param}"]`);
    }

    function filterProjectFilterMenu(input) {
        const menu = input?.closest('[data-project-filter-menu]');
        if (!menu) return;

        const query = normalizeFilterText(input.value || '');
        const emptyState = menu.querySelector('[data-project-filter-empty]');
        let visibleMatches = 0;

        menu.querySelectorAll('[data-project-filter-option]').forEach(option => {
            const value = option.dataset.projectFilterValue || '';
            const isAllOption = value === '';
            const label = normalizeFilterText(option.textContent || '');
            const isVisible = isAllOption || !query || label.includes(query);
            option.hidden = !isVisible;
            if (isVisible && !isAllOption) {
                visibleMatches += 1;
            }
        });

        if (emptyState) {
            emptyState.hidden = !query || visibleMatches > 0;
        }
    }

    function resetProjectFilterMenuSearch(menu) {
        const input = menu?.querySelector('[data-project-filter-search]');
        if (!input) return;
        input.value = '';
        filterProjectFilterMenu(input);
    }

    function scheduleServerProjectSearch() {
        if (!usesServerDirectoryFilters || !projectSearchForm) return;
        window.clearTimeout(projectSearchDebounceTimer);
        projectSearchDebounceTimer = window.setTimeout(() => {
            navigateProjectWindow();
        }, 360);
    }

    function setProjectSortValue(value) {
        if (!projectSortInput) return;
        projectSortInput.value = value === projectDefaultSort ? '' : value;
    }

    if (projectSearchForm && usesServerDirectoryFilters) {
        projectSearchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            window.clearTimeout(projectSearchDebounceTimer);
            navigateProjectWindow();
        }, pageListenerOptions);
    }

    projectFilterToggles.forEach(toggle => {
        toggle.addEventListener('click', function(event) {
            event.stopPropagation();
            const menu = this.closest('[data-project-filter-menu]');
            if (!menu) return;
            const isOpen = !menu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeProjectSortMenu();
            closeProjectFilterMenus(menu);
            closeDirectoryMembersMenus();
            closeIssuePickers();
            closeInlineSelectDropdowns();
            closeProjectPageSizeDropdown();
            closeTaskStatusPageSizeDropdowns();
            menu.classList.toggle('is-open', isOpen);
            this.setAttribute('aria-expanded', String(isOpen));
            if (isOpen) {
                resetProjectFilterMenuSearch(menu);
                setTimeout(() => menu.querySelector('[data-project-filter-search]')?.focus(), 30);
            }
        }, pageListenerOptions);
    });

    projectFilterMenus.forEach(menu => {
        menu.addEventListener('click', function(event) {
            event.stopPropagation();
        }, pageListenerOptions);
    });

    projectFilterSearchInputs.forEach(input => {
        input.addEventListener('click', event => event.stopPropagation(), pageListenerOptions);
        input.addEventListener('input', function() {
            filterProjectFilterMenu(this);
        }, pageListenerOptions);
        input.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
            }
            if (event.key === 'Escape') {
                event.stopPropagation();
                closeProjectFilterMenus();
            }
        }, pageListenerOptions);
    });

    projectFilterOptions.forEach(option => {
        option.addEventListener('click', function() {
            const param = this.dataset.projectFilterParam || '';
            const input = getProjectFilterInput(param);
            if (!input) return;
            input.value = this.dataset.projectFilterValue || '';
            closeProjectFilterMenus();
            navigateProjectWindow();
        }, pageListenerOptions);
    });

    if (projectSortToggle && projectSortMenu) {
        projectSortToggle.addEventListener('click', function(event) {
            event.stopPropagation();
            const isOpen = !projectSortMenu.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeProjectFilterMenus();
            closeDirectoryMembersMenus();
            closeIssuePickers();
            closeInlineSelectDropdowns();
            closeProjectPageSizeDropdown();
            closeTaskStatusPageSizeDropdowns();
            projectSortMenu.classList.toggle('is-open', isOpen);
            projectSortToggle.setAttribute('aria-expanded', String(isOpen));
        }, pageListenerOptions);

        projectSortMenu.addEventListener('click', function(event) {
            event.stopPropagation();
        }, pageListenerOptions);
    }

    projectSortOptions.forEach(option => {
        option.addEventListener('click', function() {
            setProjectSortValue(this.dataset.projectSortValue || projectDefaultSort);
            closeProjectSortMenu();
            navigateProjectWindow();
        }, pageListenerOptions);
    });

    if (filterStatus) {
        filterStatus.addEventListener('change', function() {
            if (usesServerDirectoryFilters) {
                navigateProjectWindow();
                return;
            }
            applyFilters();
        });
    }
    if (filterPriority) {
        filterPriority.addEventListener('change', function() {
            if (usesServerDirectoryFilters) {
                navigateProjectWindow();
                return;
            }
            applyFilters();
        });
    }
    if (filterSearch) {
        filterSearch.addEventListener('input', function() {
            if (usesServerDirectoryFilters) {
                scheduleServerProjectSearch();
                return;
            }
            applyFilters();
        });
    }
    filterSearchButtons.forEach(button => {
        button.addEventListener('click', function() {
            applyFilters();
            filterSearch?.focus();
        });
    });

    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            if (this.dataset.statusFilter !== undefined && filterStatus) {
                filterStatus.value = this.dataset.statusFilter;
            }
            if (this.dataset.priorityFilter !== undefined && filterPriority) {
                filterPriority.value = this.dataset.priorityFilter;
            }
            if (usesServerDirectoryFilters && (this.dataset.priorityFilter !== undefined || this.dataset.statusFilter !== undefined)) {
                closeStatusFilterMenu();
                closePriorityFilterMenu();
                navigateProjectWindow();
                return;
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

    if (projectPageSizeDropdown && projectPageSizeToggle) {
        syncProjectPageSizeDropdown();

        projectPageSizeToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = !projectPageSizeDropdown.classList.contains('is-open');
            closeCreateMenu();
            closeProjectActionMenus();
            closeSectionActionMenu();
            closeStatusFilterMenu();
            closePriorityFilterMenu();
            closeProjectFilterMenus();
            closeProjectSortMenu();
            closeDirectoryMembersMenus();
            closeIssuePickers();
            closeInlineSelectDropdowns();
            closeTaskStatusPageSizeDropdowns();
            projectPageSizeDropdown.classList.toggle('is-open', isOpen);
            projectPageSizeToggle.setAttribute('aria-expanded', String(isOpen));
        }, pageListenerOptions);

        projectPageSizeDropdown.addEventListener('click', function(e) {
            e.stopPropagation();
        }, pageListenerOptions);

        projectPageSizeOptions.forEach(button => {
            button.addEventListener('click', function() {
                if (!projectPageSizeSelect || !this.dataset.projectPageSizeValue) return;

                const previousValue = projectPageSizeSelect.value;
                projectPageSizeSelect.value = this.dataset.projectPageSizeValue;
                syncProjectPageSizeDropdown();
                closeProjectPageSizeDropdown();
                if (projectPageSizeSelect.value !== previousValue) {
                    projectPageSizeSelect.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }, pageListenerOptions);
        });
    }

    if (projectPageSizeSelect) {
        syncProjectPageSizeDropdown();
        projectPageSizeSelect.addEventListener('change', function() {
            syncProjectPageSizeDropdown();
            if (usesServerProjectPagination) {
                navigateProjectWindow();
                return;
            }
            projectPaginationPage = 1;
            applyProjectPagination();
            updateGroupVisibility();
            updateSelection();
        }, pageListenerOptions);
    }

    if (projectPagePrev) {
        projectPagePrev.addEventListener('click', function() {
            if (this.disabled) return;
            if (usesServerProjectPagination) {
                const url = this.dataset.projectPageUrl || '';
                if (url) navigateWithinApp(url);
                return;
            }
            setProjectPaginationPage(projectPaginationPage - 1);
        }, pageListenerOptions);
    }

    if (projectPageNext) {
        projectPageNext.addEventListener('click', function() {
            if (this.disabled) return;
            if (usesServerProjectPagination) {
                const url = this.dataset.projectPageUrl || '';
                if (url) navigateWithinApp(url);
                return;
            }
            setProjectPaginationPage(projectPaginationPage + 1);
        }, pageListenerOptions);
    }

    if (projectPaginationPages) {
        projectPaginationPages.addEventListener('click', function(event) {
            const button = event.target.closest('[data-project-page]');
            if (!button) return;

            if (usesServerProjectPagination) {
                const url = button.dataset.projectPageUrl || '';
                if (url) navigateWithinApp(url);
                return;
            }

            const page = Number.parseInt(button.dataset.projectPage || '', 10);
            if (!Number.isFinite(page) || page === projectPaginationPage) return;

            setProjectPaginationPage(page);
        }, pageListenerOptions);
    }

    taskStatusPaginations.forEach(pagination => {
        const pageSizeDropdown = pagination.querySelector('[data-task-status-page-size-dropdown]');
        const pageSizeToggle = pagination.querySelector('[data-task-status-page-size-toggle]');

        if (pageSizeDropdown && pageSizeToggle) {
            pageSizeToggle.addEventListener('click', function(event) {
                event.stopPropagation();
                const isOpen = !pageSizeDropdown.classList.contains('is-open');
                closeCreateMenu();
                closeProjectActionMenus();
                closeSectionActionMenu();
                closeStatusFilterMenu();
                closePriorityFilterMenu();
                closeDirectoryMembersMenus();
                closeIssuePickers();
                closeInlineSelectDropdowns();
                closeProjectPageSizeDropdown();
                closeTaskStatusPageSizeDropdowns(pageSizeDropdown);
                pageSizeDropdown.classList.toggle('is-open', isOpen);
                pageSizeToggle.setAttribute('aria-expanded', String(isOpen));
            }, pageListenerOptions);

            pageSizeDropdown.addEventListener('click', function(event) {
                event.stopPropagation();
                const button = event.target.closest('[data-task-status-page-url]');
                if (!button || button.disabled) return;

                const url = button.dataset.taskStatusPageUrl || '';
                if (!url) return;
                closeTaskStatusPageSizeDropdowns();
                navigateTaskStatusPage(url, pagination);
            }, pageListenerOptions);
        }

        pagination.addEventListener('click', function(event) {
            const button = event.target.closest('[data-task-status-page-url]');
            if (!button || button.disabled) return;

            const url = button.dataset.taskStatusPageUrl || '';
            if (!url) return;
            closeTaskStatusPageSizeDropdowns();
            navigateTaskStatusPage(url, pagination);
        }, pageListenerOptions);
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

    applyFilters();

    // Helper functions

    function enhanceDescriptionEditor(input) {
        if (!input) return null;

        const editor = document.createElement('div');
        editor.className = `${input.className} tasks-description-editor`;
        editor.contentEditable = input.disabled ? 'false' : 'true';
        editor.setAttribute('role', 'textbox');
        editor.setAttribute('aria-multiline', 'true');
        if (input.disabled) editor.setAttribute('aria-readonly', 'true');
        editor.dataset.placeholder = input.getAttribute('placeholder') || '';
        editor.innerHTML = descriptionValueToEditorHtml(input.value);

        input.hidden = true;
        input.classList.add('tasks-description-source');
        input.insertAdjacentElement('afterend', editor);

        if (!input.disabled) {
            editor.addEventListener('input', function() {
                syncDescriptionInput(editor);
            });
        }

        const form = input.closest('form');
        if (form && !input.disabled) {
            form.addEventListener('submit', function() {
                syncDescriptionInput(editor);
            });
        }

        syncDescriptionInput(editor);
        return editor;
    }

    function initDirectoryColumnResize() {
        const boards = document.querySelectorAll('.tasks-directory-board.tasks-directory-sheet, .tasks-directory-board.contacts-directory-sheet');
        const resetButtons = document.querySelectorAll('[data-directory-table-reset]');
        const columnManagers = document.querySelectorAll('[data-directory-column-manager]');
        if (!boards.length) return;

        const defaultDirectoryColumnWidth = 250;
        const defaultDirectoryColumnMinWidth = 50;
        const columnDefaultWidths = {
            action: 40,
            info: 40,
            project_code: 190,
            project: 320,
            section: 320,
            notes: 40,
            description: 320,
            progress: 220,
            due_at: 170,
            tasks_count: 130,
            priority: 170,
            last_activity: 210,
            company: 220,
            project_name: 220,
            members: 210,
            default_assignee: 230,
            created_at: 130,
            spacer: 0
        };
        const tagColumnDefaultWidths = {
            notes: 40,
            tag_name: 250,
            tag_code: 250,
            tag_type: 140,
            tag_visual: 160,
            priority: 140,
            scope: 140,
            owner: 190,
            status: 140,
            usage_notes: 260,
            automation: 260,
            related_tags: 220,
            task_count: 250
        };
        const columnMinimums = {
            select: 18,
            action: 40,
            info: 40,
            project_code: 150,
            project: 150,
            section: 150,
            notes: 40,
            description: 150,
            progress: 120,
            due_at: 112,
            tasks_count: 92,
            priority: 112,
            last_activity: 140,
            company: 140,
            default_assignee: 150,
            created_at: 112,
            spacer: 0
        };
        const tagColumnMinimums = {
            notes: 40,
            tag_name: 150,
            tag_code: 150,
            tag_type: 110,
            tag_visual: 130,
            priority: 112,
            scope: 112,
            owner: 140,
            status: 112,
            usage_notes: 160,
            automation: 160,
            related_tags: 150,
            task_count: 120
        };
        const fixedColumns = new Set(['spacer']);
        const nonResizableColumns = new Set(['action', 'info', 'notes', 'spacer']);
        const resizeMediaQuery = typeof window.matchMedia === 'function'
            ? window.matchMedia('(min-width: 901px)')
            : { matches: true };
        let activeResize = null;
        const taskDirectoryBoards = Array.from(boards).filter(isUniformDirectoryBoard);
        const managedDirectoryBoards = taskDirectoryBoards.filter(isManagedDirectoryBoard);
        const columnManagerDrafts = new WeakMap();

        managedDirectoryBoards.forEach(ensureDirectoryDefaultColumnOrder);
        initDirectoryColumnManagers();

        resetButtons.forEach(button => {
            button.hidden = !taskDirectoryBoards.length;
            if (!taskDirectoryBoards.length) return;

            button.addEventListener('click', () => {
                managedDirectoryBoards.forEach(board => {
                    removeStoredDirectoryColumnLayout(board);
                    applyDirectoryColumnLayout(board);
                });
                taskDirectoryBoards.forEach(resetDirectoryBoard);
                renderDirectoryColumnManagers();
                closeDirectoryColumnManagers();
                showMessage('Zresetowano ustawienia tabeli', 'success');
            }, pageListenerOptions);
        });

        boards.forEach(board => {
            const header = board.querySelector('.tasks-directory-header');
            if (!header || header.dataset.directoryResizeReady === 'true') return;

            header.dataset.directoryResizeReady = 'true';

            applyDirectoryColumnLayout(board);

            const cells = getDirectoryHeaderCells(board, header, true);
            cells.forEach(cell => {
                const column = cell.dataset.column || '';
                if (!isResizableDirectoryColumn(column)) return;
                if (cell.querySelector('[data-directory-column-resizer]')) return;

                const handle = document.createElement('button');
                const label = getDirectoryColumnLabel(cell);
                handle.type = 'button';
                handle.className = 'tasks-directory-column-resizer';
                handle.dataset.directoryColumnResizer = column;
                handle.setAttribute('aria-label', `Zmień szerokość kolumny ${label}`);
                handle.setAttribute('title', 'Przeciągnij, aby zmienić szerokość kolumny');

                handle.addEventListener('pointerdown', event => {
                    if (event.button !== undefined && event.button !== 0) return;

                    const state = createDirectoryResizeState(board, header, getDirectoryHeaderCells(board, header), cell, handle, event.clientX);
                    if (!state) return;

                    event.preventDefault();
                    activeResize = state;
                    handle.setPointerCapture(event.pointerId);
                    handle.classList.add('is-active');
                    board.classList.add('is-resizing-columns');
                    document.body.classList.add('is-resizing-directory-columns');
                });

                handle.addEventListener('pointermove', event => {
                    if (!activeResize || activeResize.handle !== handle) return;
                    updateDirectoryResize(activeResize, event.clientX - activeResize.startX);
                });

                handle.addEventListener('pointerup', finishDirectoryResize);
                handle.addEventListener('pointercancel', finishDirectoryResize);

                handle.addEventListener('keydown', event => {
                    const step = event.shiftKey ? 48 : 24;
                    let delta = 0;

                    if (event.key === 'ArrowLeft') {
                        delta = -step;
                    } else if (event.key === 'ArrowRight') {
                        delta = step;
                    } else {
                        return;
                    }

                    const state = createDirectoryResizeState(board, header, getDirectoryHeaderCells(board, header), cell, handle, 0);
                    if (!state) return;

                    event.preventDefault();
                    updateDirectoryResize(state, delta);
                    storeDirectoryWidths(state);
                });

                handle.addEventListener('click', event => {
                    event.preventDefault();
                });

                cell.appendChild(handle);
            });

            syncDirectoryResizeGrid(board);
        });

        renderDirectoryColumnManagers();

        if (columnManagers.length) {
            document.addEventListener('click', event => {
                if (!event.target.closest('[data-directory-column-manager]')) {
                    closeDirectoryColumnManagers();
                }
            }, pageListenerOptions);
        }

        const syncAllDirectoryResizeGrids = () => {
            boards.forEach(syncDirectoryResizeGrid);
        };

        if (typeof resizeMediaQuery.addEventListener === 'function') {
            resizeMediaQuery.addEventListener('change', syncAllDirectoryResizeGrids, pageListenerOptions);
        } else if (typeof resizeMediaQuery.addListener === 'function') {
            resizeMediaQuery.addListener(syncAllDirectoryResizeGrids);
        }

        function createDirectoryResizeState(board, header, cells, cell, handle, startX) {
            if (!isDirectoryResizeEnabled(header)) return null;

            const columnIndex = cells.indexOf(cell);
            const widths = getDirectoryTrackWidths(header, cells);

            if (columnIndex < 0 || !widths[columnIndex]) {
                return null;
            }

            setDirectoryGrid(board, cells, widths);

            return {
                board,
                header,
                cells,
                handle,
                startX,
                widths,
                columnIndex,
                startColumnWidth: widths[columnIndex],
                columnMinWidth: getDirectoryColumnMinWidth(cell.dataset.column, cell)
            };
        }

        function updateDirectoryResize(state, delta) {
            const minDelta = state.columnMinWidth - state.startColumnWidth;
            const clampedDelta = Math.max(delta, minDelta);
            const nextWidths = state.widths.slice();

            nextWidths[state.columnIndex] = Math.round(state.startColumnWidth + clampedDelta);
            state.widths = nextWidths;
            setDirectoryGrid(state.board, state.cells, nextWidths);
        }

        function finishDirectoryResize(event) {
            if (!activeResize) return;

            const state = activeResize;
            activeResize = null;
            state.handle.classList.remove('is-active');
            state.board.classList.remove('is-resizing-columns');
            document.body.classList.remove('is-resizing-directory-columns');
            storeDirectoryWidths(state);

            if (event.pointerId !== undefined && state.handle.hasPointerCapture(event.pointerId)) {
                state.handle.releasePointerCapture(event.pointerId);
            }
        }

        function applyStoredDirectoryWidths(board) {
            const header = board.querySelector('.tasks-directory-header');
            if (!header) return;
            if (!isDirectoryResizeEnabled(header)) return;

            const cells = getDirectoryHeaderCells(board, header);
            const storedWidths = readStoredDirectoryWidths(cells);
            if (!Object.keys(storedWidths).length) {
                if (isUniformDirectoryBoard(board)) {
                    setDirectoryGrid(board, cells, getDefaultDirectoryTrackWidths(cells));
                }
                return;
            }

            const widths = isUniformDirectoryBoard(board)
                ? getDefaultDirectoryTrackWidths(cells)
                : getDirectoryTrackWidths(header, cells);
            let hasStoredColumn = false;

            cells.forEach((cell, index) => {
                if (!isResizableDirectoryColumn(cell.dataset.column)) return;

                const storageColumn = getDirectoryStorageColumn(cell.dataset.column);
                const storedWidth = storedWidths[storageColumn];

                if (!storedWidth) return;

                widths[index] = Math.max(getDirectoryColumnMinWidth(cell.dataset.column, cell), Math.round(storedWidth));
                hasStoredColumn = true;
            });

            if (hasStoredColumn) {
                setDirectoryGrid(board, cells, widths);
            }
        }

        function getDirectoryHeaderCells(board, header, includeHidden = false) {
            return Array.from(header.querySelectorAll('[data-column]')).filter(cell => {
                return !shouldIgnoreDirectoryColumn(board, cell.dataset.column || '');
            }).filter(cell => {
                return includeHidden || !cell.hidden;
            });
        }

        function shouldIgnoreDirectoryColumn(board, column) {
            return isUniformDirectoryBoard(board) && column === 'spacer';
        }

        function getDirectoryTrackWidths(header, cells) {
            const tracks = window.getComputedStyle(header).gridTemplateColumns
                .split(/\s+/)
                .map(value => Number.parseFloat(value))
                .filter(Number.isFinite);

            if (tracks.length >= cells.length) {
                return tracks.slice(0, cells.length).map(width => Math.round(width));
            }

            return cells.map(cell => Math.round(cell.getBoundingClientRect().width));
        }

        function syncDirectoryResizeGrid(board) {
            const header = board.querySelector('.tasks-directory-header');

            if (!header || !isDirectoryResizeEnabled(header)) {
                board.style.removeProperty('--tasks-directory-grid');
                return;
            }

            applyStoredDirectoryWidths(board);
        }

        function resetDirectoryBoard(board) {
            const header = board.querySelector('.tasks-directory-header');
            if (!header || !isDirectoryResizeEnabled(header)) return;

            const cells = getDirectoryHeaderCells(board, header);
            removeStoredDirectoryWidths(cells);
            setDirectoryGrid(board, cells, getDefaultDirectoryTrackWidths(cells));
        }

        function isDirectoryHeaderVisible(header) {
            return header.getClientRects().length > 0;
        }

        function isDirectoryResizeEnabled(header) {
            return resizeMediaQuery.matches && isDirectoryHeaderVisible(header);
        }

        function setDirectoryGrid(board, cells, widths) {
            const tracks = widths.map(width => `${Math.round(width)}px`);

            board.style.setProperty('--tasks-directory-grid', tracks.join(' '));
        }

        function getDefaultDirectoryTrackWidths(cells) {
            return cells.map(cell => {
                const column = cell.dataset.column || '';
                if (column === 'select') return getDirectorySelectColumnWidth(cell);
                if (isTagDirectoryCell(cell) && Object.prototype.hasOwnProperty.call(tagColumnDefaultWidths, column)) {
                    return tagColumnDefaultWidths[column];
                }
                if (Object.prototype.hasOwnProperty.call(columnDefaultWidths, column)) {
                    return columnDefaultWidths[column];
                }
                return defaultDirectoryColumnWidth;
            });
        }

        function getDirectorySelectColumnWidth(cell) {
            const board = cell.closest('.tasks-directory-board');
            const source = board || cell;
            const configuredWidth = Number.parseFloat(
                window.getComputedStyle(source).getPropertyValue('--tasks-directory-select-width')
            );

            if (Number.isFinite(configuredWidth) && configuredWidth > 0) {
                return Math.round(configuredWidth);
            }

            return getDirectoryColumnMinWidth('select', cell);
        }

        function getDirectoryColumnMinWidth(column, sourceCell = null) {
            if (isTagDirectoryCell(sourceCell) && Object.prototype.hasOwnProperty.call(tagColumnMinimums, column)) {
                return tagColumnMinimums[column];
            }
            if (Object.prototype.hasOwnProperty.call(columnMinimums, column)) {
                return columnMinimums[column];
            }
            return defaultDirectoryColumnMinWidth;
        }

        function isTagDirectoryCell(cell) {
            return Boolean(cell?.closest('.tasks-tag-sheet'));
        }

        function getDirectoryStorageColumn(column) {
            return column || '';
        }

        function getDirectoryStorageSegment() {
            const pathSegment = window.location.pathname.split('/').filter(Boolean)[0] || '';

            if (pathSegment === 'contacts') return 'contacts';
            if (pathSegment === 'kanban') return 'kanban';
            return taskAppSegment;
        }

        function getDirectoryStorageKey(cells) {
            const schema = cells
                .map(cell => getDirectoryStorageColumn(cell.dataset.column))
                .filter(Boolean)
                .join('-') || 'default';

            return `${getDirectoryStorageSegment()}:directoryColumnWidths:v4:${schema}`;
        }

        function isFixedDirectoryColumn(column) {
            return fixedColumns.has(column);
        }

        function isResizableDirectoryColumn(column) {
            return column && column !== 'select' && !nonResizableColumns.has(column);
        }

        function isUniformDirectoryBoard(board) {
            return board.classList.contains('tasks-directory-sheet') && !board.classList.contains('contacts-directory-sheet');
        }

        function isManagedDirectoryBoard(board) {
            return board.classList.contains('tasks-project-sheet--selectable')
                || board.classList.contains('tasks-tag-sheet');
        }

        function getDirectoryColumnLabel(cell) {
            const label = cell?.dataset.columnLabel || cell?.textContent || cell?.getAttribute('aria-label') || cell?.getAttribute('title') || 'kolumny';
            return label.replace(/\s+/g, ' ').trim().toLowerCase();
        }

        function getDirectoryColumnDisplayLabel(cell) {
            const label = getDirectoryColumnLabel(cell);
            return label ? label.charAt(0).toUpperCase() + label.slice(1) : 'Kolumna';
        }

        function readStoredDirectoryWidths(cells) {
            const storageKey = getDirectoryStorageKey(cells);
            return readStoredDirectoryWidthsByKey(storageKey);
        }

        function readStoredDirectoryWidthsByKey(storageKey) {
            try {
                const value = JSON.parse(window.localStorage.getItem(storageKey) || '{}');
                return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
            } catch (error) {
                return {};
            }
        }

        function storeDirectoryWidths(state) {
            const widths = state.widths;
            const nextStoredWidths = {};

            state.cells.forEach((cell, index) => {
                const column = cell.dataset.column;
                if (!isResizableDirectoryColumn(column)) return;

                nextStoredWidths[getDirectoryStorageColumn(column)] = Math.round(widths[index]);
            });

            try {
                window.localStorage.setItem(getDirectoryStorageKey(state.cells), JSON.stringify(nextStoredWidths));
            } catch (error) {
                // localStorage may be unavailable in private or restricted contexts.
            }
        }

        function removeStoredDirectoryWidths(cells) {
            const schema = cells
                .map(cell => getDirectoryStorageColumn(cell.dataset.column))
                .filter(Boolean)
                .join('-') || 'default';
            const segment = getDirectoryStorageSegment();
            const keys = new Set([
                getDirectoryStorageKey(cells),
                `${segment}:directoryColumnWidths:v3:${schema}`,
                `${segment}:directoryColumnWidths:${schema}`,
                `${taskAppSegment}:directoryColumnWidths`
            ]);

            try {
                keys.forEach(key => window.localStorage.removeItem(key));
            } catch (error) {
                // localStorage may be unavailable in private or restricted contexts.
            }
        }

        function initDirectoryColumnManagers() {
            if (!columnManagers.length) return;

            columnManagers.forEach(manager => {
                const board = managedDirectoryBoards[0] || null;
                const toggle = manager.querySelector('[data-directory-column-manager-toggle]');
                const search = manager.querySelector('[data-directory-column-manager-search]');
                const saveButton = manager.querySelector('[data-directory-column-manager-save]');
                const cancelButton = manager.querySelector('[data-directory-column-manager-cancel]');

                manager.hidden = !board;
                if (!board || !toggle || manager.dataset.directoryColumnManagerReady === 'true') return;

                manager.dataset.directoryColumnManagerReady = 'true';
                manager.dataset.directoryColumnManagerBoard = getDirectoryColumnLayoutStorageKey(board);

                toggle.addEventListener('click', event => {
                    event.stopPropagation();
                    const willOpen = !manager.classList.contains('is-open');
                    closeDirectoryColumnManagers(manager);
                    if (willOpen) {
                        openDirectoryColumnManager(manager, board);
                    } else {
                        closeDirectoryColumnManagers();
                    }
                }, pageListenerOptions);

                search?.addEventListener('input', () => {
                    renderDirectoryColumnManager(manager, board);
                }, pageListenerOptions);

                search?.addEventListener('keydown', event => {
                    if (event.key === 'Escape') {
                        event.stopPropagation();
                        closeDirectoryColumnManagers();
                    }
                }, pageListenerOptions);

                saveButton?.addEventListener('click', () => {
                    saveDirectoryColumnManager(manager, board);
                }, pageListenerOptions);

                cancelButton?.addEventListener('click', () => {
                    closeDirectoryColumnManagers();
                }, pageListenerOptions);
            });
        }

        function renderDirectoryColumnManagers() {
            columnManagers.forEach(manager => {
                const board = managedDirectoryBoards[0] || null;
                manager.hidden = !board;
                if (board) renderDirectoryColumnManager(manager, board);
            });
        }

        function renderDirectoryColumnManager(manager, board) {
            const list = manager.querySelector('[data-directory-column-manager-list]');
            if (!list) return;

            const header = board.querySelector('.tasks-directory-header');
            if (!header) return;

            const draft = getDirectoryColumnManagerDraft(manager, board);
            const hiddenColumns = new Set(draft.hidden);
            const searchTerm = getDirectoryColumnManagerSearchTerm(manager);
            let visibleCount = 0;

            list.innerHTML = '';

            draft.order.forEach(column => {
                const cell = header.querySelector(`[data-column="${cssEscape(column)}"]`);
                const item = document.createElement('label');
                const checkbox = document.createElement('input');
                const label = document.createElement('span');
                const drag = document.createElement('span');
                const displayLabel = getDirectoryColumnDisplayLabel(cell);

                if (searchTerm && !displayLabel.toLowerCase().includes(searchTerm)) {
                    return;
                }

                visibleCount += 1;

                item.className = 'tasks-directory-column-item';
                item.draggable = true;
                item.dataset.directoryColumnItem = column;

                checkbox.type = 'checkbox';
                checkbox.checked = !hiddenColumns.has(column);
                checkbox.dataset.directoryColumnToggle = column;
                checkbox.setAttribute('aria-label', getDirectoryColumnLabel(cell));

                label.textContent = displayLabel;

                drag.className = 'tasks-directory-column-drag';
                drag.innerHTML = '<i data-lucide="grip-vertical" aria-hidden="true"></i>';

                item.appendChild(checkbox);
                item.appendChild(label);
                item.appendChild(drag);
                list.appendChild(item);

                checkbox.addEventListener('change', () => {
                    updateDirectoryColumnDraftVisibility(manager, board, column, checkbox.checked);
                    renderDirectoryColumnManager(manager, board);
                }, pageListenerOptions);

                item.addEventListener('dragstart', event => {
                    item.classList.add('is-dragging');
                    event.dataTransfer.effectAllowed = 'move';
                    event.dataTransfer.setData('text/plain', column);
                }, pageListenerOptions);

                item.addEventListener('dragend', () => {
                    item.classList.remove('is-dragging');
                }, pageListenerOptions);
            });

            if (!visibleCount) {
                const empty = document.createElement('div');
                empty.className = 'tasks-directory-column-empty';
                empty.textContent = 'Brak kolumn';
                list.appendChild(empty);
            }

            list.ondragover = event => {
                const draggingItem = list.querySelector('.tasks-directory-column-item.is-dragging');
                if (!draggingItem) return;

                event.preventDefault();
                const afterItem = getDirectoryColumnManagerItemAfterPointer(list, event.clientY);
                if (afterItem) {
                    list.insertBefore(draggingItem, afterItem);
                } else {
                    list.appendChild(draggingItem);
                }
            };

            list.ondrop = event => {
                const filteredOrder = Array.from(list.querySelectorAll('[data-directory-column-item]'))
                    .map(item => item.dataset.directoryColumnItem)
                    .filter(Boolean);

                event.preventDefault();
                updateDirectoryColumnDraftOrder(manager, board, filteredOrder);
                renderDirectoryColumnManager(manager, board);
            };

            if (window.AncoreIcons?.render) {
                window.AncoreIcons.render(list);
            } else if (window.lucide?.createIcons) {
                window.lucide.createIcons();
            }
        }

        function openDirectoryColumnManager(manager, board) {
            const toggle = manager.querySelector('[data-directory-column-manager-toggle]');
            const search = manager.querySelector('[data-directory-column-manager-search]');

            columnManagerDrafts.set(manager, createDirectoryColumnManagerDraft(board));
            if (search) search.value = '';

            manager.classList.add('is-open');
            toggle?.setAttribute('aria-expanded', 'true');
            renderDirectoryColumnManager(manager, board);
            window.setTimeout(() => search?.focus(), 0);
        }

        function saveDirectoryColumnManager(manager, board) {
            const draft = getDirectoryColumnManagerDraft(manager, board);

            writeStoredDirectoryColumnLayout(board, {
                order: draft.order,
                hidden: draft.hidden
            });
            applyDirectoryColumnLayout(board);
            syncDirectoryResizeGrid(board);
            closeDirectoryColumnManagers();
        }

        function closeDirectoryColumnManagers(exceptManager = null) {
            columnManagers.forEach(manager => {
                if (manager === exceptManager) return;
                manager.classList.remove('is-open');
                manager.querySelector('[data-directory-column-manager-toggle]')?.setAttribute('aria-expanded', 'false');
                columnManagerDrafts.delete(manager);
            });
        }

        function createDirectoryColumnManagerDraft(board) {
            return {
                order: getDirectoryManagedColumns(board),
                hidden: readStoredDirectoryColumnLayout(board).hidden
            };
        }

        function getDirectoryColumnManagerDraft(manager, board) {
            if (!columnManagerDrafts.has(manager)) {
                columnManagerDrafts.set(manager, createDirectoryColumnManagerDraft(board));
            }
            return columnManagerDrafts.get(manager);
        }

        function getDirectoryColumnManagerSearchTerm(manager) {
            return (manager.querySelector('[data-directory-column-manager-search]')?.value || '').trim().toLowerCase();
        }

        function updateDirectoryColumnDraftVisibility(manager, board, column, isVisible) {
            const draft = getDirectoryColumnManagerDraft(manager, board);
            const hidden = new Set(draft.hidden);

            if (isVisible) {
                hidden.delete(column);
            } else if (draft.order.filter(item => !hidden.has(item)).length > 1) {
                hidden.add(column);
            }

            draft.hidden = Array.from(hidden);
        }

        function updateDirectoryColumnDraftOrder(manager, board, filteredOrder) {
            const draft = getDirectoryColumnManagerDraft(manager, board);
            const filteredSet = new Set(filteredOrder);
            const untouchedColumns = draft.order.filter(column => !filteredSet.has(column));
            const nextOrder = [];
            let insertedFilteredOrder = false;

            draft.order.forEach(column => {
                if (filteredSet.has(column)) {
                    if (!insertedFilteredOrder) {
                        nextOrder.push(...filteredOrder);
                        insertedFilteredOrder = true;
                    }
                    return;
                }
                if (untouchedColumns.includes(column)) nextOrder.push(column);
            });

            draft.order = nextOrder.filter((column, index, columns) => columns.indexOf(column) === index);
        }

        function getDirectoryManagedColumns(board) {
            const header = board.querySelector('.tasks-directory-header');
            if (!header) return [];

            const storedLayout = readStoredDirectoryColumnLayout(board);
            const defaultColumns = getDirectoryDefaultColumnOrder(board)
                .filter(column => column && !isDirectoryColumnLayoutFixed(column) && !shouldIgnoreDirectoryColumn(board, column));
            const defaultSet = new Set(defaultColumns);
            const orderedColumns = storedLayout.order.filter(column => defaultSet.has(column));
            const orderedSet = new Set(orderedColumns);

            defaultColumns.forEach(column => {
                if (orderedSet.has(column)) return;

                const nextColumn = defaultColumns
                    .slice(defaultColumns.indexOf(column) + 1)
                    .find(nextDefaultColumn => orderedSet.has(nextDefaultColumn));

                if (nextColumn) {
                    orderedColumns.splice(orderedColumns.indexOf(nextColumn), 0, column);
                } else {
                    orderedColumns.push(column);
                }

                orderedSet.add(column);
            });

            return orderedColumns;
        }

        function applyDirectoryColumnLayout(board) {
            if (!isManagedDirectoryBoard(board)) return;

            const header = board.querySelector('.tasks-directory-header');
            if (!header) return;

            const columns = getDirectoryManagedColumns(board);
            const hiddenColumns = new Set(readStoredDirectoryColumnLayout(board).hidden);
            const fixedOrderedColumns = getDirectoryDefaultColumnOrder(board)
                .filter(column => column && isDirectoryColumnLayoutFixed(column) && column !== 'select' && column !== 'spacer');
            const orderedColumns = ['select', ...fixedOrderedColumns, ...columns, 'spacer'];

            [header, ...board.querySelectorAll('.tasks-directory-list .tasks-directory-row')].forEach(row => {
                const cells = Array.from(row.querySelectorAll(':scope > [data-column]'));
                const cellsByColumn = new Map(cells.map(cell => [cell.dataset.column || '', cell]));

                orderedColumns.forEach(column => {
                    const cell = cellsByColumn.get(column);
                    if (cell) row.appendChild(cell);
                });

                cells.forEach(cell => {
                    const column = cell.dataset.column || '';
                    if (!orderedColumns.includes(column)) row.appendChild(cell);
                    cell.hidden = hiddenColumns.has(column) && !isDirectoryColumnLayoutFixed(column);
                });

                markDirectoryLastVisibleColumn(row);
            });
        }

        function markDirectoryLastVisibleColumn(row) {
            const cells = Array.from(row.querySelectorAll(':scope > [data-column]'));

            cells.forEach(cell => cell.classList.remove('is-directory-last-visible'));

            const lastVisibleCell = cells.filter(cell => {
                const column = cell.dataset.column || '';
                return column !== 'select' && column !== 'spacer' && !cell.hidden;
            }).pop();

            lastVisibleCell?.classList.add('is-directory-last-visible');
        }

        function updateDirectoryColumnVisibility(board, column, isVisible) {
            const layout = readStoredDirectoryColumnLayout(board);
            const hidden = new Set(layout.hidden);

            if (isVisible) {
                hidden.delete(column);
            } else if (getDirectoryVisibleManagedColumns(board).length > 1) {
                hidden.add(column);
            }

            writeStoredDirectoryColumnLayout(board, {
                order: getDirectoryManagedColumns(board),
                hidden: Array.from(hidden)
            });
            applyDirectoryColumnLayout(board);
            syncDirectoryResizeGrid(board);
        }

        function updateDirectoryColumnOrder(board, order) {
            const validColumns = new Set(getDirectoryManagedColumns(board));
            const nextOrder = order.filter(column => validColumns.has(column));

            getDirectoryManagedColumns(board).forEach(column => {
                if (!nextOrder.includes(column)) nextOrder.push(column);
            });

            writeStoredDirectoryColumnLayout(board, {
                order: nextOrder,
                hidden: readStoredDirectoryColumnLayout(board).hidden
            });
            applyDirectoryColumnLayout(board);
            syncDirectoryResizeGrid(board);
        }

        function getDirectoryVisibleManagedColumns(board) {
            const hiddenColumns = new Set(readStoredDirectoryColumnLayout(board).hidden);
            return getDirectoryManagedColumns(board).filter(column => !hiddenColumns.has(column));
        }

        function getDirectoryColumnManagerItemAfterPointer(list, pointerY) {
            const items = Array.from(list.querySelectorAll('.tasks-directory-column-item:not(.is-dragging)'));

            return items.reduce((closest, item) => {
                const box = item.getBoundingClientRect();
                const offset = pointerY - box.top - box.height / 2;
                if (offset < 0 && offset > closest.offset) {
                    return { offset, item };
                }
                return closest;
            }, { offset: Number.NEGATIVE_INFINITY, item: null }).item;
        }

        function isDirectoryColumnLayoutFixed(column) {
            return column === 'select' || isFixedDirectoryColumn(column);
        }

        function getDirectoryColumnLayoutStorageKey(board) {
            const schema = getDirectoryDefaultColumnOrder(board)
                .map(column => getDirectoryStorageColumn(column))
                .filter(Boolean)
                .join('-') || 'default';

            return `${getDirectoryStorageSegment()}:directoryColumnLayout:v2:${schema}`;
        }

        function ensureDirectoryDefaultColumnOrder(board) {
            if (board.dataset.directoryDefaultColumnOrder) return;

            const header = board.querySelector('.tasks-directory-header');
            const columns = header
                ? Array.from(header.querySelectorAll('[data-column]')).map(cell => cell.dataset.column || '').filter(Boolean)
                : [];

            board.dataset.directoryDefaultColumnOrder = JSON.stringify(columns);
        }

        function getDirectoryDefaultColumnOrder(board) {
            ensureDirectoryDefaultColumnOrder(board);

            try {
                const columns = JSON.parse(board.dataset.directoryDefaultColumnOrder || '[]');
                return Array.isArray(columns) ? columns.filter(Boolean) : [];
            } catch (error) {
                return [];
            }
        }

        function readStoredDirectoryColumnLayout(board) {
            try {
                const value = JSON.parse(window.localStorage.getItem(getDirectoryColumnLayoutStorageKey(board)) || '{}');
                return {
                    order: Array.isArray(value.order) ? value.order.filter(Boolean) : [],
                    hidden: Array.isArray(value.hidden) ? value.hidden.filter(Boolean) : []
                };
            } catch (error) {
                return { order: [], hidden: [] };
            }
        }

        function writeStoredDirectoryColumnLayout(board, layout) {
            try {
                window.localStorage.setItem(getDirectoryColumnLayoutStorageKey(board), JSON.stringify(layout));
            } catch (error) {
                // localStorage may be unavailable in private or restricted contexts.
            }
        }

        function removeStoredDirectoryColumnLayout(board) {
            try {
                window.localStorage.removeItem(getDirectoryColumnLayoutStorageKey(board));
            } catch (error) {
                // localStorage may be unavailable in private or restricted contexts.
            }
        }

        function cssEscape(value) {
            if (window.CSS && typeof window.CSS.escape === 'function') {
                return window.CSS.escape(value);
            }
            return String(value).replace(/"/g, '\\"');
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
        if (window.showNotification) {
            window.showNotification(message, type);
            return;
        }

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
    const sortIcon = button.querySelector('[data-task-sort-icon], [data-lucide]');
    const iconName = direction === 'asc' ? 'arrow-up-wide-narrow' : 'arrow-down-wide-narrow';

    button.dataset.sortDirection = direction;
    button.setAttribute('aria-pressed', String(direction === 'asc'));
    button.setAttribute('title', direction === 'asc' ? 'Sortowanie: rosnąco' : 'Sortowanie: malejąco');
    button.setAttribute('aria-label', direction === 'asc' ? 'Sortowanie: rosnąco' : 'Sortowanie: malejąco');

    if (sortArrowHead) {
        sortArrowHead.setAttribute('d', direction === 'asc' ? 'M5 7l3-3 3 3' : 'M5 17l3 3 3-3');
    }

    if (sortIcon && sortIcon.getAttribute('data-lucide') !== iconName) {
        const icon = document.createElement('i');
        icon.setAttribute('data-lucide', iconName);
        icon.setAttribute('aria-hidden', 'true');
        icon.setAttribute('data-task-sort-icon', '');
        sortIcon.replaceWith(icon);

        if (window.AncoreIcons?.render) {
            window.AncoreIcons.render(button);
        } else if (window.lucide?.createIcons) {
            window.lucide.createIcons();
        }
    }
}

if (!window.ancoreTaskSortHandlerInitialized) {
    window.ancoreTaskSortHandlerInitialized = true;

    document.addEventListener('click', function(event) {
        const button = event.target.closest('[data-task-sort]');
        if (!button) return;
        if (button.hasAttribute('data-project-sort-toggle')) return;

        const direction = button.dataset.sortDirection === 'asc' ? 'desc' : 'asc';
        updateTaskSortButton(button, direction);
        sortCurrentTaskLists(direction);
        if (typeof window.ancoreRefreshProjectPagination === 'function') {
            window.ancoreRefreshProjectPagination();
        }
    });
}

if (!window.ancoreContactActionMenusInitialized) {
    window.ancoreContactActionMenusInitialized = true;

    function closeContactActionMenus(exceptMenu = null) {
        document.querySelectorAll('[data-contact-actions]').forEach((menu) => {
            if (menu === exceptMenu) return;
            menu.classList.remove('is-open');
            menu.querySelector('[data-contact-actions-toggle]')?.setAttribute('aria-expanded', 'false');
        });
    }

    document.addEventListener('click', function(event) {
        const toggle = event.target.closest('[data-contact-actions-toggle]');
        if (toggle) {
            const menu = toggle.closest('[data-contact-actions]');
            if (!menu) return;

            event.preventDefault();
            event.stopPropagation();

            const isOpen = !menu.classList.contains('is-open');
            closeContactActionMenus(menu);
            menu.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
            return;
        }

        if (!event.target.closest('[data-contact-actions]')) {
            closeContactActionMenus();
        }
    });

    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            closeContactActionMenus();
        }
    });

    document.addEventListener('submit', function(event) {
        const form = event.target.closest('[data-confirm-delete]');
        if (!form) return;

        if (!window.confirm(form.dataset.confirmDelete || 'Usunąć element?')) {
            event.preventDefault();
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTasksPage);
} else {
    initTasksPage();
}

document.addEventListener('ancore:content-loaded', initTasksPage);
