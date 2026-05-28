(function () {
    const configEl = document.getElementById('kanban-config');
    if (!configEl) return;
    const config = JSON.parse(configEl.textContent);
    const csrfToken = config.csrfToken;
    const urls = config.urls;
    const configBoardId = String(config.boardId);

    function apiUrl(key, id) {
        const pattern = urls[key];
        return id !== undefined && id !== null
            ? pattern.replace('__ID__', String(id))
            : pattern;
    }

    function boardIndexUrl(workspaceId, boardId) {
        const params = new URLSearchParams();
        if (workspaceId) params.set('workspace_id', workspaceId);
        if (boardId) params.set('board_id', boardId);
        const qs = params.toString();
        return qs ? `${urls.index}?${qs}` : urls.index;
    }

    function initKanban() {
        const boardElement = document.getElementById('kanban-board');
        if (!boardElement) return;
        

        // 1. Initialize Sortable for Columns (moving columns)
        new Sortable(boardElement, {
            animation: 150,
            handle: '.column-header',
            draggable: '.kanban-column',
            ghostClass: 'sortable-ghost',
            onEnd: function () {
                const columnIds = Array.from(boardElement.querySelectorAll('.kanban-column'))
                    .map(col => col.dataset.columnId);

                fetch(urls.reorderColumns, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ column_ids: columnIds })
                });
            }
        });

        // 2. Initialize Sortable for Cards in each column
        function initCardSortable(columnElement) {
            new Sortable(columnElement, {
                group: 'cards',
                animation: 150,
                ghostClass: 'sortable-ghost',
                onEnd: function (evt) {
                    const targetColId = evt.to.dataset.columnId;
                    const cardIds = Array.from(evt.to.querySelectorAll('.kanban-card'))
                        .map(card => card.dataset.cardId);

                    fetch(urls.reorderCards, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({
                            column_id: targetColId,
                            card_ids: cardIds
                        })
                    });

                    // Update counts
                    updateColumnCounts();
                }
            });
        }

        document.querySelectorAll('.column-cards').forEach(initCardSortable);

        function updateColumnCounts() {
            document.querySelectorAll('.kanban-column').forEach(col => {
                const count = col.querySelectorAll('.kanban-card').length;
                col.querySelector('.column-count').textContent = count;
            });
        }

        // 3. Inline Column Name Editing
        document.querySelectorAll('.column-title').forEach(title => {
            title.addEventListener('blur', function () {
                const newName = this.innerText.trim();
                const colId = this.closest('.kanban-column').dataset.columnId;

                if (newName && newName !== this.dataset.oldName) {
                    fetch(apiUrl('columnUpdateName', colId), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ name: newName })
                    });
                    this.dataset.oldName = newName;
                }
            });

            title.addEventListener('focus', function () {
                this.dataset.oldName = this.innerText.trim();
                // Select all text
                const range = document.createRange();
                range.selectNodeContents(this);
                const sel = window.getSelection();
                sel.removeAllRanges();
                sel.addRange(range);
            });

            title.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.blur();
                }
            });
        });

        // 4. Quick Add Card
        document.querySelectorAll('.btn-add-card').forEach(btn => {
            btn.addEventListener('click', function () {
                const container = this.closest('.quick-add-card');
                this.style.display = 'none';
                container.querySelector('.quick-add-form').style.display = 'block';
                container.querySelector('textarea').focus();
            });
        });

        document.querySelectorAll('.cancel-quick-add').forEach(btn => {
            btn.addEventListener('click', function () {
                const container = this.closest('.quick-add-card');
                container.querySelector('.quick-add-form').style.display = 'none';
                container.querySelector('.btn-add-card').style.display = 'flex';
            });
        });

        document.querySelectorAll('.submit-quick-add').forEach(btn => {
            btn.addEventListener('click', function () {
                const container = this.closest('.quick-add-card');
                const textarea = container.querySelector('textarea');
                const title = textarea.value.trim();
                const columnId = this.closest('.kanban-column').dataset.columnId;

                if (title) {
                    const formData = new FormData();
                    formData.append('title', title);
                    formData.append('column', columnId);
                    formData.append('is_ajax', 'true');
                    formData.append('csrfmiddlewaretoken', csrfToken);

                    fetch(urls.createCard, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    })
                        .then(res => res.json())
                        .then(data => {
                            if (data.status === 'success') {
                                location.reload();
                            } else {
                                alert('Błąd: ' + JSON.stringify(data.errors || data.message));
                            }
                        });
                }
            });
        });

        document.querySelectorAll('.quick-add-form textarea').forEach(textarea => {
            textarea.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.closest('.quick-add-card').querySelector('.submit-quick-add').click();
                }
                if (e.key === 'Escape') {
                    this.closest('.quick-add-card').querySelector('.cancel-quick-add').click();
                }
            });
        });

        // 5. Modals and Column Addition
        const detailModal = document.getElementById('card-detail-modal');
        const addColumnBtn = document.getElementById('show-add-column');
        const addColumnForm = document.querySelector('.add-column-form');
        const addColumnInput = document.getElementById('new-column-name');

        // Inline Add Column
        if (addColumnBtn) {
            addColumnBtn.addEventListener('click', () => {
                addColumnBtn.style.display = 'none';
                addColumnForm.style.display = 'block';
                addColumnInput.focus();
            });
        }

        document.getElementById('cancel-add-column').addEventListener('click', () => {
            addColumnForm.style.display = 'none';
            addColumnBtn.style.display = 'flex';
            addColumnInput.value = '';
        });

        document.getElementById('submit-add-column').addEventListener('click', function () {
            const name = addColumnInput.value.trim();
            if (name) {
                const formData = new FormData();
                formData.append('name', name);
                formData.append('board_id', configBoardId);
                formData.append('is_ajax', 'true');
                formData.append('csrfmiddlewaretoken', csrfToken);

                fetch(urls.createColumn, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') location.reload();
                    });
            }
        });

        // Handle Enter and Esc for Add Column
        addColumnInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') document.getElementById('submit-add-column').click();
            if (e.key === 'Escape') document.getElementById('cancel-add-column').click();
        });

        let panelOpenCard = null;

        function closeCardPanel() {
            detailModal.classList.remove('active');
            detailModal.setAttribute('aria-hidden', 'true');
            if (panelOpenCard) {
                panelOpenCard.classList.remove('is-panel-open');
                panelOpenCard = null;
            }
        }

        function openCardPanel(cardEl) {
            if (panelOpenCard && panelOpenCard !== cardEl) {
                panelOpenCard.classList.remove('is-panel-open');
            }
            panelOpenCard = cardEl;
            cardEl.classList.add('is-panel-open');
            detailModal.classList.add('active');
            detailModal.setAttribute('aria-hidden', 'false');
        }

        document.querySelectorAll('.cancel-modal-btn').forEach(btn => {
            btn.addEventListener('click', closeCardPanel);
        });

        detailModal.addEventListener('click', function (e) {
            if (e.target === detailModal) {
                closeCardPanel();
            }
        });

        // 6. Card Details and Editing
        let currentCardId = null;
        let cardState = {};

        document.querySelectorAll('.kanban-card').forEach(card => {
            card.addEventListener('click', function () {
                currentCardId = this.dataset.cardId;
                fetch(apiUrl('cardDetail', currentCardId))
                    .then(res => res.json())
                    .then(data => {
                        cardState = data;
                        document.getElementById('detail-title-input').value = data.title;
                        document.getElementById('detail-description-input').value = data.description || '';
                        document.getElementById('detail-column').textContent = data.column_name;
                        document.getElementById('detail-date').textContent = data.created_at;

                        renderAttachments(data.attachments || []);
                        openCardPanel(this);
                    });
            });
        });

        // Save card updates on change — with autosave indicator
        const autosaveStatus = document.getElementById('autosave-status');
        let saveTimer = null;

        function showSaving() {
            autosaveStatus.textContent = 'Zapisywanie...';
            autosaveStatus.className = 'kmodal-save-indicator';
        }
        function showSaved() {
            autosaveStatus.textContent = 'Zapisano';
            autosaveStatus.className = 'kmodal-save-indicator saved';
            setTimeout(() => { autosaveStatus.textContent = ''; autosaveStatus.className = 'kmodal-save-indicator'; }, 2500);
        }

        function saveCardUpdate() {
            if (!currentCardId) return;
            const title = document.getElementById('detail-title-input').value.trim();
            const description = document.getElementById('detail-description-input').value.trim();

            if (!title) return;
            showSaving();

            fetch(apiUrl('cardUpdate', currentCardId), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify({ title, description })
            }).then(res => res.json())
                .then(data => {
                    if (data.status === 'success') {
                        showSaved();
                        const card = document.querySelector(`.kanban-card[data-card-id="${currentCardId}"]`);
                        if (card) {
                            card.querySelector('.card-title').textContent = title;
                            const descPrev = card.querySelector('.card-desc-preview');
                            if (descPrev) descPrev.textContent = description.substring(0, 80) + (description.length > 80 ? '...' : '');
                        }
                    }
                });
        }

        // Debounced auto-save on input (500ms after typing stops)
        function debouncedSave() {
            clearTimeout(saveTimer);
            saveTimer = setTimeout(saveCardUpdate, 500);
        }

        document.getElementById('detail-title-input').addEventListener('input', debouncedSave);
        document.getElementById('detail-description-input').addEventListener('input', debouncedSave);

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && detailModal.classList.contains('active')) {
                saveCardUpdate();
                closeCardPanel();
            }
        });

        // Modal close buttons already handle closing via the cancel-modal-btn class


        // 7. Delete Column
        document.querySelectorAll('.delete-column-btn').forEach(btn => {
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                if (confirm('Czy na pewno chcesz usunąć tę listę wraz ze wszystkimi kartami?')) {
                    const colId = this.closest('.kanban-column').dataset.columnId;
                    fetch(apiUrl('columnDelete', colId), {
                        method: 'POST',
                        headers: { 'X-CSRFToken': csrfToken }
                    }).then(() => location.reload());
                }
            });
        });

        // 8. Delete Card (from modal)
        document.querySelector('.delete-card-btn').addEventListener('click', function () {
            if (currentCardId && confirm('Czy na pewno chcesz usunąć tę kartę?')) {
                fetch(apiUrl('cardDelete', currentCardId), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken }
                }).then(() => location.reload());
            }
        });


        // 10. Toggle Complete (from card checkbox)
        document.addEventListener('change', function (e) {
            if (e.target.classList.contains('card-checkbox')) {
                const card = e.target.closest('.kanban-card');
                const cardId = card.dataset.cardId;

                fetch(apiUrl('cardToggle', cardId), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken }
                }).then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            card.classList.toggle('completed', data.is_completed);
                        }
                    });
            }
        });

        // Prevent modal opening when clicking checkbox
        document.addEventListener('click', function (e) {
            if (e.target.classList.contains('card-checkbox') || e.target.classList.contains('card-checkbox-container')) {
                e.stopPropagation();
            }
        }, true);

        // =========================================================
        // ATTACHMENTS
        // =========================================================
        const dropzone = document.getElementById('attach-dropzone');
        const fileInput = document.getElementById('attach-file-input');
        const progressWrap = document.getElementById('attach-progress-wrap');
        const progressBar = document.getElementById('attach-progress-bar');
        const progressLabel = document.getElementById('attach-progress-label');
        const attachList = document.getElementById('attach-list');

        function renderAttachments(attachments) {
            attachList.innerHTML = '';
            attachments.forEach(a => addAttachmentRow(a));
        }

        function addAttachmentRow(a) {
            const typeClass = AttachmentIcons.extensionToTypeClass(a.extension);
            const row = document.createElement('div');
            row.className = 'attach-item';
            row.dataset.attachId = a.id;
            row.innerHTML = `
            ${AttachmentIcons.iconHtmlByExtension(a.extension, 'md')}
            <div class="attach-info">
                <a href="${a.url}" target="_blank" class="attach-name" title="${a.name}">${a.name}</a>
                <span class="attach-date">${a.uploaded_at}</span>
            </div>
            <button class="attach-delete-btn attachment-delete-btn" data-attach-id="${a.id}" title="Usuń załącznik">
                <i class="bi ${AttachmentIcons.TRASH}" aria-hidden="true"></i>
            </button>
        `;
            attachList.appendChild(row);

            row.querySelector('.attach-delete-btn').addEventListener('click', function () {
                const attId = this.dataset.attachId;
                if (!confirm('Usunąć ten załącznik?')) return;
                fetch(apiUrl('attachmentDelete', attId), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken }
                }).then(r => r.json()).then(data => {
                    if (data.status === 'success') {
                        row.remove();
                    }
                });
            });
        }

        function uploadFiles(files) {
            if (!currentCardId || !files.length) return;
            const file = files[0]; // upload one by one
            const formData = new FormData();
            formData.append('file', file);
            formData.append('csrfmiddlewaretoken', csrfToken);

            progressWrap.hidden = false;
            progressWrap.style.display = 'flex';
            progressBar.style.width = '0%';
            progressLabel.textContent = `Wgrywanie: ${file.name}`;

            const xhr = new XMLHttpRequest();
            xhr.open('POST', apiUrl('cardUploadAttachment', currentCardId));
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

            xhr.upload.addEventListener('progress', function (e) {
                if (e.lengthComputable) {
                    const pct = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = pct + '%';
                    progressLabel.textContent = `Wgrywanie: ${pct}%`;
                }
            });

            xhr.addEventListener('load', function () {
                progressWrap.hidden = true;
                progressWrap.style.display = 'none';
                try {
                    const data = JSON.parse(xhr.responseText);
                    if (data.status === 'success') {
                        addAttachmentRow(data.attachment);
                        // If there are more files, upload next
                        if (files.length > 1) uploadFiles(Array.from(files).slice(1));
                    } else {
                        alert('Błąd: ' + (data.message || 'Nieznany błąd'));
                    }
                } catch (err) {
                    alert('Błąd serwera');
                }
            });

            xhr.addEventListener('error', function () {
                progressWrap.hidden = true;
                progressWrap.style.display = 'none';
                alert('Błąd połączenia podczas wgrywania pliku.');
            });

            xhr.send(formData);
        }

        // File input change
        fileInput.addEventListener('change', function () {
            uploadFiles(Array.from(this.files));
            this.value = '';
        });

        // Drag & drop
        dropzone.addEventListener('dragover', function (e) {
            e.preventDefault();
            dropzone.classList.add('drag-over');
        });
        dropzone.addEventListener('dragleave', function () {
            dropzone.classList.remove('drag-over');
        });
        dropzone.addEventListener('drop', function (e) {
            e.preventDefault();
            dropzone.classList.remove('drag-over');
            if (e.dataTransfer.files.length) {
                uploadFiles(Array.from(e.dataTransfer.files));
            }
        });

        // =========================================================
        // WORKSPACE & BOARD SWITHCER AND CRUD
        // =========================================================
        
        // Selector changes
        const workspaceSelector = document.getElementById('workspace-selector');
        if (workspaceSelector) {
            workspaceSelector.addEventListener('change', function () {
                window.location.href = boardIndexUrl(this.value);
            });
        }

        const boardSelector = document.getElementById('board-selector');
        if (boardSelector) {
            boardSelector.addEventListener('change', function () {
                const wsId = workspaceSelector ? workspaceSelector.value : '';
                window.location.href = boardIndexUrl(wsId, this.value);
            });
        }

        // Modals opening/closing
        const wsModal = document.getElementById('workspace-modal');
        const boardModal = document.getElementById('board-modal');
        const backgroundModal = document.getElementById('background-modal');
        const kanbanWorkspace = document.getElementById('kanban-workspace');
        const boardId = kanbanWorkspace?.dataset.boardId;

        const addWsBtn = document.getElementById('add-workspace-btn');
        if (addWsBtn) {
            addWsBtn.addEventListener('click', function () {
                wsModal.classList.add('active');
            });
        }

        const addBoardBtn = document.getElementById('add-board-btn');
        if (addBoardBtn) {
            addBoardBtn.addEventListener('click', function () {
                boardModal.classList.add('active');
            });
        }

        document.querySelectorAll('.close-ws-modal').forEach(btn => {
            btn.addEventListener('click', function () {
                wsModal.classList.remove('active');
            });
        });

        document.querySelectorAll('.close-board-modal').forEach(btn => {
            btn.addEventListener('click', function () {
                boardModal.classList.remove('active');
            });
        });

        // Close on overlay click
        wsModal.addEventListener('click', function (e) {
            if (e.target === wsModal) wsModal.classList.remove('active');
        });
        boardModal.addEventListener('click', function (e) {
            if (e.target === boardModal) boardModal.classList.remove('active');
        });

        const boardBackgroundBtn = document.getElementById('board-background-btn');
        if (boardBackgroundBtn && backgroundModal) {
            boardBackgroundBtn.addEventListener('click', function () {
                backgroundModal.classList.add('active');
            });
        }

        document.querySelectorAll('.close-background-modal').forEach(btn => {
            btn.addEventListener('click', function () {
                backgroundModal.classList.remove('active');
            });
        });

        backgroundModal?.addEventListener('click', function (e) {
            if (e.target === backgroundModal) backgroundModal.classList.remove('active');
        });

        const backgroundError = document.getElementById('background-error');
        const backgroundUrlInput = document.getElementById('background-url-input');
        const backgroundFileInput = document.getElementById('background-file-input');

        function showBackgroundError(msg) {
            if (!backgroundError) return;
            if (msg) {
                backgroundError.textContent = msg;
                backgroundError.hidden = false;
            } else {
                backgroundError.hidden = true;
                backgroundError.textContent = '';
            }
        }

        const backgroundPreview = document.getElementById('board-background-preview');

        function applyBoardBackground(data) {
            if (!kanbanWorkspace) return;
            kanbanWorkspace.style.background = data.background_style;
            kanbanWorkspace.dataset.background = data.background || '';
            kanbanWorkspace.dataset.backgroundSource = data.background_source || 'preset';

            const useWallpaper = data.background_source !== 'preset' || (data.background && data.background !== 'neutral');
            kanbanWorkspace.classList.toggle('kanban-workspace--wallpaper', useWallpaper);

            document.querySelectorAll('.board-background-option').forEach(opt => {
                const isPreset = data.background_source === 'preset';
                opt.classList.toggle('is-selected', isPreset && opt.dataset.background === data.background);
            });

            if (backgroundUrlInput && data.background_source === 'url') {
                backgroundUrlInput.value = data.background_url || '';
            } else if (backgroundUrlInput && data.background_source === 'preset') {
                backgroundUrlInput.value = '';
            }

            if (backgroundPreview) {
                if (data.background_source === 'image' || data.background_source === 'url') {
                    backgroundPreview.style.background = data.background_style;
                    backgroundPreview.hidden = false;
                } else {
                    backgroundPreview.hidden = true;
                }
            }

            showBackgroundError('');
        }

        async function postBoardBackground(body) {
            const res = await fetch(apiUrl('boardBackground', boardId), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(body),
            });
            const data = await res.json();
            if (data.status !== 'success') {
                showBackgroundError(data.message || 'Nie udało się zapisać tapety');
                return null;
            }
            return data;
        }

        document.querySelectorAll('.board-background-option').forEach(btn => {
            btn.addEventListener('click', async function () {
                const background = this.dataset.background;
                if (!boardId) return;
                if (kanbanWorkspace.dataset.backgroundSource === 'preset' && background === kanbanWorkspace.dataset.background) {
                    backgroundModal.classList.remove('active');
                    return;
                }
                try {
                    const data = await postBoardBackground({ background });
                    if (data) {
                        applyBoardBackground(data);
                        backgroundModal.classList.remove('active');
                    }
                } catch (err) {
                    console.error('Błąd zapisu tapety:', err);
                    showBackgroundError('Błąd połączenia z serwerem');
                }
            });
        });

        document.getElementById('background-url-btn')?.addEventListener('click', async function () {
            if (!boardId || !backgroundUrlInput) return;
            const url = backgroundUrlInput.value.trim();
            if (!url) {
                showBackgroundError('Podaj adres URL obrazu');
                return;
            }
            try {
                const data = await postBoardBackground({ background_url: url });
                if (data) {
                    applyBoardBackground(data);
                    backgroundModal.classList.remove('active');
                }
            } catch (err) {
                console.error('Błąd zapisu tapety:', err);
                showBackgroundError('Błąd połączenia z serwerem');
            }
        });

        document.getElementById('background-upload-btn')?.addEventListener('click', async function () {
            if (!boardId || !backgroundFileInput?.files?.length) {
                showBackgroundError('Wybierz plik obrazu');
                return;
            }
            const formData = new FormData();
            formData.append('background_image', backgroundFileInput.files[0]);
            showBackgroundError('');
            try {
                const res = await fetch(apiUrl('boardBackgroundUpload', boardId), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                    body: formData,
                });
                const data = await res.json();
                if (data.status === 'success') {
                    applyBoardBackground(data);
                    backgroundFileInput.value = '';
                    backgroundModal.classList.remove('active');
                } else {
                    showBackgroundError(data.message || 'Nie udało się wgrać pliku');
                }
            } catch (err) {
                console.error('Błąd wgrywania tapety:', err);
                showBackgroundError('Błąd połączenia z serwerem');
            }
        });

        // Renaming Workspace
        const renameWsBtn = document.getElementById('rename-workspace-btn');
        if (renameWsBtn) {
            renameWsBtn.addEventListener('click', function () {
                const currentName = workspaceSelector.options[workspaceSelector.selectedIndex].text;
                const newName = prompt("Zmień nazwę przestrzeni roboczej:", currentName);
                if (newName && newName.trim() && newName.trim() !== currentName) {
                    const wsId = workspaceSelector.value;
                    fetch(apiUrl('workspaceRename', wsId), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ name: newName.trim() })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            window.location.reload();
                        } else {
                            alert('Błąd: ' + data.message);
                        }
                    });
                }
            });
        }

        // Renaming Board
        const renameBoardBtn = document.getElementById('rename-board-btn');
        if (renameBoardBtn) {
            renameBoardBtn.addEventListener('click', function () {
                const currentName = boardSelector.options[boardSelector.selectedIndex].text;
                const newName = prompt("Zmień nazwę tablicy:", currentName);
                if (newName && newName.trim() && newName.trim() !== currentName) {
                    const boardId = boardSelector.value;
                    fetch(apiUrl('boardRename', boardId), {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': csrfToken
                        },
                        body: JSON.stringify({ name: newName.trim() })
                    })
                    .then(res => res.json())
                    .then(data => {
                        if (data.status === 'success') {
                            window.location.reload();
                        } else {
                            alert('Błąd: ' + data.message);
                        }
                    });
                }
            });
        }

        // Deleting Workspace & Board (Confirmations)
        const deleteWsBtn = document.getElementById('delete-workspace-btn');
        if (deleteWsBtn) {
            deleteWsBtn.addEventListener('click', function (e) {
                e.preventDefault();
                const currentName = workspaceSelector.options[workspaceSelector.selectedIndex].text;
                if (confirm(`Czy na pewno chcesz usunąć przestrzeń roboczą "${currentName}" wraz ze wszystkimi jej tablicami i zadaniami?`)) {
                    document.getElementById('delete-workspace-form').submit();
                }
            });
        }

        const deleteBoardBtn = document.getElementById('delete-board-btn');
        if (deleteBoardBtn) {
            deleteBoardBtn.addEventListener('click', function (e) {
                e.preventDefault();
                const currentName = boardSelector.options[boardSelector.selectedIndex].text;
                if (confirm(`Czy na pewno chcesz usunąć tablicę "${currentName}" wraz ze wszystkimi jej zadaniami?`)) {
                    document.getElementById('delete-board-form').submit();
                }
            });
        }

    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initKanban, { once: true });
    } else {
        initKanban();
    }
})();
