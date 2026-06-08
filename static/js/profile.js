(function () {
    function editModal() {
        return document.querySelector('[data-profile-edit-modal]');
    }

    function openEditModal() {
        const modal = editModal();
        if (!modal) return;

        closeProfileActionMenus(null);
        modal.classList.add('is-open');
        modal.setAttribute('aria-hidden', 'false');
        document.body.classList.add('profile-edit-modal-open');

        const firstControl = modal.querySelector('input:not([type="hidden"]):not([hidden]), textarea, button');
        firstControl?.focus();
    }

    function closeEditModal() {
        const modal = editModal();
        if (!modal) return;

        closeOtherDropdowns(null);
        modal.classList.remove('is-open');
        modal.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('profile-edit-modal-open');
    }

    function closeDropdown(dropdown) {
        const toggle = dropdown.querySelector('[data-profile-status-toggle]');
        const menu = dropdown.querySelector('[data-profile-status-menu]');

        dropdown.classList.remove('is-open');
        toggle?.setAttribute('aria-expanded', 'false');
        if (menu) {
            menu.hidden = true;
        }
    }

    function closeOtherDropdowns(activeDropdown) {
        document.querySelectorAll('[data-profile-status-dropdown].is-open').forEach(dropdown => {
            if (dropdown !== activeDropdown) {
                closeDropdown(dropdown);
            }
        });
    }

    function closeProfileActionMenu(menu, restoreFocus = false) {
        const toggle = menu.querySelector('[data-profile-actions-toggle]');

        menu.classList.remove('is-open');
        toggle?.setAttribute('aria-expanded', 'false');
        if (restoreFocus) {
            toggle?.focus();
        }
    }

    function closeProfileActionMenus(exceptMenu) {
        document.querySelectorAll('[data-profile-actions].is-open').forEach(menu => {
            if (menu !== exceptMenu) {
                closeProfileActionMenu(menu);
            }
        });
    }

    function toggleProfileActionMenu(toggle) {
        const menu = toggle.closest('[data-profile-actions]');
        if (!menu) return;

        const isOpen = !menu.classList.contains('is-open');
        closeOtherDropdowns(null);
        closeProfileActionMenus(menu);
        menu.classList.toggle('is-open', isOpen);
        toggle.setAttribute('aria-expanded', String(isOpen));
    }

    function openDropdown(dropdown) {
        const toggle = dropdown.querySelector('[data-profile-status-toggle]');
        const menu = dropdown.querySelector('[data-profile-status-menu]');

        closeOtherDropdowns(dropdown);
        dropdown.classList.add('is-open');
        toggle?.setAttribute('aria-expanded', 'true');
        if (menu) {
            menu.hidden = false;
        }
    }

    function selectedOption(dropdown) {
        return dropdown.querySelector('[data-profile-status-option].is-selected')
            || dropdown.querySelector('[data-profile-status-option]');
    }

    function syncDropdown(dropdown, value, dispatchChange) {
        const select = dropdown.querySelector('select');
        const escapedValue = window.CSS?.escape ? CSS.escape(value) : String(value).replace(/"/g, '\\"');
        const option = dropdown.querySelector(`[data-profile-status-option][data-value="${escapedValue}"]`)
            || dropdown.querySelector('[data-profile-status-option]');
        const toggle = dropdown.querySelector('[data-profile-status-toggle]');
        const selectedIcon = dropdown.querySelector('[data-profile-status-selected-icon]');
        const selectedLabel = dropdown.querySelector('[data-profile-status-selected-label]');

        if (!select || !option) return;

        select.value = option.dataset.value || '';
        if (toggle) {
            Array.from(toggle.classList)
                .filter(className => className.startsWith('presence-'))
                .forEach(className => toggle.classList.remove(className));
            toggle.classList.add(`presence-${option.dataset.value || ''}`);
        }

        dropdown.querySelectorAll('[data-profile-status-option]').forEach(item => {
            const isSelected = item === option;
            item.classList.toggle('is-selected', isSelected);
            item.setAttribute('aria-selected', String(isSelected));
        });

        if (selectedIcon) {
            const optionIcon = option.querySelector('[data-profile-status-option-icon]');
            selectedIcon.className = `profile-status-button-icon presence-${option.dataset.value || ''}`;
            selectedIcon.innerHTML = optionIcon ? optionIcon.innerHTML : '';
        }

        if (selectedLabel) {
            selectedLabel.textContent = option.dataset.label || option.textContent.trim();
        }

        if (dispatchChange) {
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function focusOption(dropdown, direction) {
        const options = Array.from(dropdown.querySelectorAll('[data-profile-status-option]'));
        if (!options.length) return;

        const activeIndex = Math.max(0, options.indexOf(document.activeElement));
        const selectedIndex = Math.max(0, options.indexOf(selectedOption(dropdown)));
        const currentIndex = document.activeElement && dropdown.contains(document.activeElement)
            ? activeIndex
            : selectedIndex;
        const nextIndex = (currentIndex + direction + options.length) % options.length;

        openDropdown(dropdown);
        options[nextIndex].focus();
    }

    function initDropdowns() {
        document.querySelectorAll('[data-profile-status-dropdown]').forEach(dropdown => {
            const select = dropdown.querySelector('select');
            if (select?.value) {
                syncDropdown(dropdown, select.value, false);
            }
        });
    }

    function submitStatusForm(form) {
        if (!form || form.dataset.profileStatusSubmitting === 'true') return;

        form.dataset.profileStatusSubmitting = 'true';
        form.classList.add('is-submitting');
        form.querySelectorAll('button').forEach(button => {
            button.disabled = true;
        });

        if (form.requestSubmit) {
            form.requestSubmit();
        } else {
            form.submit();
        }
    }

    function initEditModal() {
        if (editModal()?.classList.contains('is-open')) {
            document.body.classList.add('profile-edit-modal-open');
        }
    }

    function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
    }

    function initPhotoEditor(editor) {
        if (editor.dataset.profilePhotoInitialized === 'true') return;

        const fileInput = editor.querySelector('.profile-photo-input');
        const cropInput = editor.querySelector('[data-profile-photo-crop-input]');
        const cropper = editor.querySelector('[data-profile-photo-cropper]');
        const stage = editor.querySelector('[data-profile-photo-crop-stage]');
        const canvas = editor.querySelector('[data-profile-photo-canvas]');
        const zoomInput = editor.querySelector('[data-profile-photo-zoom]');
        const zoomIn = editor.querySelector('[data-profile-photo-zoom-in]');
        const zoomOut = editor.querySelector('[data-profile-photo-zoom-out]');
        const modal = editor.querySelector('[data-profile-photo-modal]');
        const emptyState = editor.querySelector('[data-profile-photo-empty]');
        const preview = editor.querySelector('[data-profile-photo-preview]');
        const fallbackTemplate = editor.querySelector('[data-profile-photo-fallback]');
        const removeInput = editor.querySelector('[data-profile-photo-remove-input]');
        const openButtons = editor.querySelectorAll('[data-profile-photo-open]');
        const closeButtons = editor.querySelectorAll('[data-profile-photo-close]');
        const changeButton = editor.querySelector('[data-profile-photo-change]');
        const removeButton = editor.querySelector('[data-profile-photo-remove]');
        const saveButton = editor.querySelector('[data-profile-photo-save]');
        const form = editor.closest('form');
        const context = canvas?.getContext('2d');
        const cropLayout = editor.closest('[data-profile-photo-layout]')
            || editor.closest('.profile-edit-body');
        const currentPhotoUrl = editor.dataset.profilePhotoUrl || '';
        const hasModal = Boolean(modal);

        if (!fileInput || !cropInput || !cropper || !stage || !canvas || !zoomInput || !context || !form) {
            return;
        }

        editor.dataset.profilePhotoInitialized = 'true';

        const state = {
            image: null,
            objectUrl: '',
            minScale: 1,
            scale: 1,
            zoom: 1,
            x: 0,
            y: 0,
            pointerId: null,
            dragStartX: 0,
            dragStartY: 0,
            startX: 0,
            startY: 0,
            shouldExport: false,
            removed: false,
        };

        function setCropperVisible(isVisible) {
            if (hasModal) {
                cropper.hidden = false;
                emptyState?.toggleAttribute('hidden', isVisible);
            } else {
                cropper.hidden = !isVisible;
                cropLayout?.classList.toggle('has-profile-cropper', isVisible);
            }
            editor.classList.toggle('is-cropping', isVisible);
        }

        function constrainPosition() {
            if (!state.image) return;

            const size = canvas.width;
            const width = state.image.naturalWidth * state.scale;
            const height = state.image.naturalHeight * state.scale;

            state.x = width <= size ? (size - width) / 2 : clamp(state.x, size - width, 0);
            state.y = height <= size ? (size - height) / 2 : clamp(state.y, size - height, 0);
        }

        function drawPhoto() {
            context.clearRect(0, 0, canvas.width, canvas.height);
            context.fillStyle = '#eef1f4';
            context.fillRect(0, 0, canvas.width, canvas.height);

            if (!state.image) return;

            context.imageSmoothingEnabled = true;
            context.imageSmoothingQuality = 'high';
            context.drawImage(
                state.image,
                state.x,
                state.y,
                state.image.naturalWidth * state.scale,
                state.image.naturalHeight * state.scale
            );
        }

        function centerPhoto() {
            if (!state.image) return;

            const size = canvas.width;
            state.minScale = Math.max(
                size / state.image.naturalWidth,
                size / state.image.naturalHeight
            );
            state.zoom = 1;
            state.scale = state.minScale;
            state.x = (size - state.image.naturalWidth * state.scale) / 2;
            state.y = (size - state.image.naturalHeight * state.scale) / 2;
            zoomInput.value = '1';
            constrainPosition();
            drawPhoto();
        }

        function markCropChanged() {
            if (!state.image) return;
            state.shouldExport = true;
            state.removed = false;
            if (removeInput) {
                removeInput.value = '';
            }
        }

        function setModalOpen(isOpen) {
            if (!modal) return;

            modal.hidden = !isOpen;
            document.body.classList.toggle('contacts-photo-editor-open', isOpen);

            if (isOpen) {
                setCropperVisible(Boolean(state.image));
                saveButton?.focus();
            }
        }

        function requestPhotoFile() {
            fileInput.value = '';
            fileInput.click();
        }

        function openPhotoEditor() {
            requestPhotoFile();
        }

        function closePhotoEditor() {
            setModalOpen(false);
        }

        function updatePreview(photoUrl) {
            if (!preview) return;

            preview.classList.toggle('has-photo', Boolean(photoUrl));
            if (photoUrl) {
                preview.innerHTML = `<img src="${photoUrl}" alt="">`;
                return;
            }

            preview.innerHTML = fallbackTemplate?.innerHTML || '';
        }

        function setZoom(nextZoom, anchorX = canvas.width / 2, anchorY = canvas.height / 2) {
            if (!state.image) return;

            const zoom = clamp(Number(nextZoom) || 1, Number(zoomInput.min), Number(zoomInput.max));
            const previousScale = state.scale;

            state.zoom = zoom;
            state.scale = state.minScale * state.zoom;

            const scaleRatio = previousScale > 0 ? state.scale / previousScale : 1;
            state.x = anchorX - (anchorX - state.x) * scaleRatio;
            state.y = anchorY - (anchorY - state.y) * scaleRatio;

            zoomInput.value = String(state.zoom);
            constrainPosition();
            drawPhoto();
        }

        function clearObjectUrl() {
            if (!state.objectUrl) return;

            URL.revokeObjectURL(state.objectUrl);
            state.objectUrl = '';
        }

        function loadPhotoSource(src, nextObjectUrl, shouldExport) {
            clearObjectUrl();

            const image = new Image();

            image.onload = () => {
                state.image = image;
                state.objectUrl = nextObjectUrl || '';
                state.shouldExport = Boolean(shouldExport);
                state.removed = false;
                cropInput.value = '';
                if (removeInput) {
                    removeInput.value = '';
                }
                setCropperVisible(true);
                centerPhoto();
                if (hasModal && shouldExport) {
                    setModalOpen(true);
                }
            };

            image.onerror = () => {
                state.image = null;
                state.shouldExport = false;
                state.removed = false;
                cropInput.value = '';
                setCropperVisible(false);
                if (nextObjectUrl) {
                    URL.revokeObjectURL(nextObjectUrl);
                }
            };

            image.src = src;
        }

        function loadPhoto(file) {
            if (!file || !file.type.startsWith('image/')) {
                state.image = null;
                state.shouldExport = false;
                state.removed = false;
                cropInput.value = '';
                setCropperVisible(false);
                return;
            }

            const objectUrl = URL.createObjectURL(file);
            loadPhotoSource(objectUrl, objectUrl, true);
        }

        function exportCrop() {
            if (!state.image) return '';

            const outputSize = 512;
            const output = document.createElement('canvas');
            const outputContext = output.getContext('2d');
            const scaleRatio = outputSize / canvas.width;

            if (!outputContext) return '';

            output.width = outputSize;
            output.height = outputSize;
            outputContext.fillStyle = '#ffffff';
            outputContext.fillRect(0, 0, outputSize, outputSize);
            outputContext.imageSmoothingEnabled = true;
            outputContext.imageSmoothingQuality = 'high';
            outputContext.drawImage(
                state.image,
                state.x * scaleRatio,
                state.y * scaleRatio,
                state.image.naturalWidth * state.scale * scaleRatio,
                state.image.naturalHeight * state.scale * scaleRatio
            );

            try {
                return output.toDataURL('image/jpeg', 0.9);
            } catch (_error) {
                return '';
            }
        }

        function changePhoto() {
            requestPhotoFile();
        }

        function removePhoto() {
            state.image = null;
            state.shouldExport = false;
            state.removed = true;
            clearObjectUrl();
            cropInput.value = '';
            fileInput.value = '';
            if (removeInput) {
                removeInput.value = '1';
            }
            updatePreview('');
            setCropperVisible(false);
            setModalOpen(false);
        }

        function savePhoto() {
            if (!state.image) {
                requestPhotoFile();
                return;
            }

            if (state.shouldExport) {
                const cropData = exportCrop();
                if (!cropData) {
                    return;
                }

                cropInput.value = cropData;
                fileInput.value = '';
                if (removeInput) {
                    removeInput.value = '';
                }
                updatePreview(cropData);
                state.shouldExport = false;
                state.removed = false;
            }

            setModalOpen(false);
        }

        fileInput.addEventListener('change', () => {
            loadPhoto(fileInput.files?.[0]);
        });

        openButtons.forEach(button => {
            button.addEventListener('click', event => {
                event.stopPropagation();
                openPhotoEditor();
            });
        });

        closeButtons.forEach(button => {
            button.addEventListener('click', event => {
                event.stopPropagation();
                closePhotoEditor();
            });
        });

        modal?.addEventListener('click', event => {
            if (event.target === modal) {
                closePhotoEditor();
            }
        });

        changeButton?.addEventListener('click', event => {
            event.stopPropagation();
            changePhoto();
        });

        removeButton?.addEventListener('click', event => {
            event.stopPropagation();
            removePhoto();
        });

        saveButton?.addEventListener('click', event => {
            event.stopPropagation();
            savePhoto();
        });

        zoomInput.addEventListener('input', () => {
            markCropChanged();
            setZoom(zoomInput.value);
        });

        zoomIn?.addEventListener('click', () => {
            markCropChanged();
            setZoom(state.zoom + 0.15);
        });

        zoomOut?.addEventListener('click', () => {
            markCropChanged();
            setZoom(state.zoom - 0.15);
        });

        stage.addEventListener('pointerdown', event => {
            if (!state.image) return;

            event.preventDefault();
            state.pointerId = event.pointerId;
            state.dragStartX = event.clientX;
            state.dragStartY = event.clientY;
            state.startX = state.x;
            state.startY = state.y;
            stage.classList.add('is-dragging');
            stage.setPointerCapture(event.pointerId);
        });

        stage.addEventListener('pointermove', event => {
            if (!state.image || state.pointerId !== event.pointerId) return;

            const rect = canvas.getBoundingClientRect();
            const moveRatio = canvas.width / rect.width;

            state.x = state.startX + (event.clientX - state.dragStartX) * moveRatio;
            state.y = state.startY + (event.clientY - state.dragStartY) * moveRatio;
            markCropChanged();
            constrainPosition();
            drawPhoto();
        });

        ['pointerup', 'pointercancel'].forEach(eventName => {
            stage.addEventListener(eventName, event => {
                if (state.pointerId !== event.pointerId) return;

                state.pointerId = null;
                stage.classList.remove('is-dragging');
                if (stage.hasPointerCapture(event.pointerId)) {
                    stage.releasePointerCapture(event.pointerId);
                }
            });
        });

        stage.addEventListener('wheel', event => {
            if (!state.image) return;

            event.preventDefault();
            const rect = canvas.getBoundingClientRect();
            const anchorX = (event.clientX - rect.left) * (canvas.width / rect.width);
            const anchorY = (event.clientY - rect.top) * (canvas.height / rect.height);
            const direction = event.deltaY > 0 ? -1 : 1;

            markCropChanged();
            setZoom(state.zoom + direction * 0.08, anchorX, anchorY);
        }, { passive: false });

        form.addEventListener('submit', () => {
            if (hasModal || !state.image || !state.shouldExport) return;

            const cropData = exportCrop();
            if (!cropData) {
                cropInput.value = '';
                return;
            }

            cropInput.value = cropData;
            fileInput.value = '';
        });

        if (currentPhotoUrl) {
            loadPhotoSource(currentPhotoUrl, '', false);
        }

        editor.profilePhotoEditorApi = {
            change: changePhoto,
            close: closePhotoEditor,
            open: openPhotoEditor,
            remove: removePhoto,
            save: savePhoto,
        };
    }

    function initPhotoEditors() {
        document.querySelectorAll('[data-profile-photo-editor]').forEach(initPhotoEditor);
    }

    document.addEventListener('click', event => {
        const photoAction = event.target.closest('[data-profile-photo-open], [data-profile-photo-close], [data-profile-photo-change], [data-profile-photo-remove], [data-profile-photo-save]');
        const editOpen = event.target.closest('[data-profile-edit-open]');
        const editClose = event.target.closest('[data-profile-edit-close]');
        const actionToggle = event.target.closest('[data-profile-actions-toggle]');
        const toggle = event.target.closest('[data-profile-status-toggle]');
        const option = event.target.closest('[data-profile-status-option]');
        const modal = editModal();

        if (photoAction) {
            const editor = photoAction.closest('[data-profile-photo-editor]');
            if (editor) {
                initPhotoEditor(editor);
                const api = editor.profilePhotoEditorApi;

                if (api) {
                    event.preventDefault();
                    event.stopPropagation();

                    if (photoAction.matches('[data-profile-photo-open]')) {
                        api.open();
                    } else if (photoAction.matches('[data-profile-photo-close]')) {
                        api.close();
                    } else if (photoAction.matches('[data-profile-photo-change]')) {
                        api.change();
                    } else if (photoAction.matches('[data-profile-photo-remove]')) {
                        api.remove();
                    } else if (photoAction.matches('[data-profile-photo-save]')) {
                        api.save();
                    }
                    return;
                }
            }
        }

        if (editOpen) {
            closeProfileActionMenus(null);
            openEditModal();
            return;
        }

        if (actionToggle) {
            event.stopPropagation();
            toggleProfileActionMenu(actionToggle);
            return;
        }

        if (editClose) {
            closeEditModal();
            return;
        }

        if (modal && event.target === modal) {
            closeEditModal();
            return;
        }

        if (toggle) {
            const dropdown = toggle.closest('[data-profile-status-dropdown]');
            if (!dropdown) return;

            if (dropdown.classList.contains('is-open')) {
                closeDropdown(dropdown);
            } else {
                openDropdown(dropdown);
            }
            return;
        }

        if (option) {
            const dropdown = option.closest('[data-profile-status-dropdown]');
            if (!dropdown) return;

            syncDropdown(dropdown, option.dataset.value || '', true);
            closeDropdown(dropdown);
            dropdown.querySelector('[data-profile-status-toggle]')?.focus();
            return;
        }

        if (!event.target.closest('[data-profile-status-dropdown]')) {
            closeOtherDropdowns(null);
        }

        if (!event.target.closest('[data-profile-actions]')) {
            closeProfileActionMenus(null);
        }
    });

    document.addEventListener('keydown', event => {
        const dropdown = event.target.closest('[data-profile-status-dropdown]');
        const actionMenu = event.target.closest('[data-profile-actions]');

        if (actionMenu && event.key === 'Escape') {
            closeProfileActionMenu(actionMenu, true);
            return;
        }

        if (dropdown && event.key === 'Escape') {
            closeDropdown(dropdown);
            dropdown.querySelector('[data-profile-status-toggle]')?.focus();
            return;
        }

        if (dropdown && event.key === 'ArrowDown') {
            event.preventDefault();
            focusOption(dropdown, 1);
            return;
        }

        if (dropdown && event.key === 'ArrowUp') {
            event.preventDefault();
            focusOption(dropdown, -1);
            return;
        }

        if (event.key === 'Escape' && editModal()?.classList.contains('is-open')) {
            closeEditModal();
        }
    });

    document.addEventListener('change', event => {
        if (!event.target.matches('[data-profile-status-dropdown] select')) return;

        const dropdown = event.target.closest('[data-profile-status-dropdown]');
        syncDropdown(dropdown, event.target.value, false);
        submitStatusForm(event.target.closest('[data-profile-status-form]'));
    });

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            initDropdowns();
            initEditModal();
            initPhotoEditors();
        });
    } else {
        initDropdowns();
        initEditModal();
        initPhotoEditors();
    }
})();
