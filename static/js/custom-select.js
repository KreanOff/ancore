(function () {
    const WRAPPER_SELECTOR = '[data-ancore-custom-select]';
    const SOURCE_ATTR = 'data-ancore-custom-select-source';
    const OPTION_SELECTOR = '[data-ancore-custom-select-option]';
    const SEARCH_ATTR = 'data-ancore-custom-select-search';
    const SEARCH_INPUT_SELECTOR = '[data-ancore-custom-select-search-input]';
    const LIST_SELECTOR = '[data-ancore-custom-select-list]';
    const CUSTOM_OPTION_SELECTOR = '[data-ancore-custom-select-custom-option]';
    const SKIP_ANCESTOR_SELECTOR = [
        '.u-sr-only',
        '[data-inline-select-dropdown]',
        '[data-task-detail-dropdown]',
        '[data-contact-custom-select]',
        '[data-calendar-color-select]',
        '[data-profile-status-dropdown]'
    ].join(', ');

    let generatedId = 0;
    let refreshTimer = null;

    function nextId(prefix) {
        generatedId += 1;
        return `${prefix}-${generatedId}`;
    }

    function isElementHidden(element) {
        if (!element || element.hidden || element.getAttribute('aria-hidden') === 'true') {
            return true;
        }

        return Boolean(element.closest('[hidden], .u-sr-only'));
    }

    function hasExistingCustomControl(select) {
        const dropdownWrap = select.closest('.tasks-issue-dropdown-wrap');
        if (dropdownWrap?.querySelector('[data-inline-select-dropdown], [data-task-detail-dropdown]')) {
            return true;
        }

        return Boolean(select.closest(SKIP_ANCESTOR_SELECTOR));
    }

    function shouldEnhance(select) {
        return select instanceof HTMLSelectElement
            && !select.closest(WRAPPER_SELECTOR)
            && !select.hasAttribute(SOURCE_ATTR)
            && !isElementHidden(select)
            && !hasExistingCustomControl(select)
            && !select.matches('[data-no-custom-select]');
    }

    function getLabelText(select) {
        const label = select.labels?.[0];
        return select.getAttribute('aria-label')
            || label?.textContent?.replace(/\s+/g, ' ').trim()
            || select.name
            || 'Wybierz opcję';
    }

    function ensureElementId(element, prefix) {
        if (!element) return '';
        if (!element.id) {
            element.id = nextId(prefix);
        }
        return element.id;
    }

    function selectedLabel(select) {
        const selected = Array.from(select.selectedOptions || []);

        if (select.multiple) {
            if (!selected.length) return select.getAttribute('data-ancore-custom-select-empty-label') || 'Wybierz opcje';
            if (selected.length === 1) return selected[0].textContent.trim();
            return `${selected.length} wybrane`;
        }

        return selected[0]?.textContent.trim() || 'Wybierz opcję';
    }

    function wrapperForSelect(select) {
        return select?.closest?.(WRAPPER_SELECTOR) || null;
    }

    function getWrapperParts(wrapper) {
        return {
            select: wrapper.querySelector(`select[${SOURCE_ATTR}]`),
            button: wrapper.querySelector('[data-ancore-custom-select-toggle]'),
            label: wrapper.querySelector('[data-ancore-custom-select-label]'),
            menu: wrapper.querySelector('[data-ancore-custom-select-menu]'),
            search: wrapper.querySelector(SEARCH_INPUT_SELECTOR),
            list: wrapper.querySelector(LIST_SELECTOR)
        };
    }

    function renderIcon(scope) {
        window.AncoreIcons?.render(scope);
    }

    function normalizedText(value) {
        return (value || '')
            .toLocaleLowerCase('pl-PL')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .replace(/ł/g, 'l');
    }

    function optionButtons(wrapper) {
        return Array.from(wrapper.querySelectorAll(`${OPTION_SELECTOR}:not(:disabled)`))
            .filter(optionButton => !optionButton.hidden);
    }

    function filterOptions(wrapper) {
        const { search, list } = getWrapperParts(wrapper);
        if (!search || !list) return;

        const query = normalizedText(search.value);
        let visibleCount = 0;

        Array.from(list.querySelectorAll(OPTION_SELECTOR)).forEach(optionButton => {
            const matches = !query || normalizedText(optionButton.textContent).includes(query);
            optionButton.hidden = !matches;
            if (matches) visibleCount += 1;
        });

        Array.from(list.querySelectorAll('.ancore-custom-select__group-label')).forEach(groupLabel => {
            let next = groupLabel.nextElementSibling;
            let hasVisibleOption = false;
            while (next && !next.classList.contains('ancore-custom-select__group-label')) {
                if (next.matches?.(OPTION_SELECTOR) && !next.hidden) {
                    hasVisibleOption = true;
                    break;
                }
                next = next.nextElementSibling;
            }
            groupLabel.hidden = !hasVisibleOption;
        });

        const empty = list.querySelector('[data-ancore-custom-select-empty]');
        if (empty) empty.hidden = visibleCount > 0;
        const customOption = wrapper.querySelector(CUSTOM_OPTION_SELECTOR);
        if (customOption) {
            const { select } = getWrapperParts(wrapper);
            const value = search.value.trim();
            customOption.hidden = !value || Array.from(select.options).some(option => option.value === value);
            customOption.textContent = value ? `Użyj „${value}”` : '';
            if (empty && !customOption.hidden) empty.hidden = true;
        }
    }

    function resetSearch(wrapper) {
        const { search } = getWrapperParts(wrapper);
        if (!search || !search.value) return;
        search.value = '';
        filterOptions(wrapper);
    }

    function optionVisual(option, select) {
        if (select?.name === 'task_type' || select?.name === 'task_group') return null;
        const templateId = option?.dataset.ancoreOptionPreview;
        const template = templateId ? document.getElementById(templateId) : null;
        if (template instanceof HTMLTemplateElement && template.content.firstElementChild) {
            const preview = template.content.firstElementChild.cloneNode(true);
            preview.classList.add('ancore-custom-select__preview');
            preview.setAttribute('aria-hidden', 'true');
            return preview;
        }
        const field = select?.name;
        const value = option?.value;
        if (field === 'priority' && ['none', 'urgent', 'high', 'medium', 'low'].includes(value)) {
            const preview = document.createElement('span');
            preview.className = `ancore-custom-select__preview tasks-row-priority priority-${value}`;
            preview.setAttribute('aria-hidden', 'true');
            preview.append(window.AncoreIcons.create({ none: 'circle', urgent: 'circle-alert', high: 'arrow-up', medium: 'equal', low: 'arrow-down' }[value]));
            return preview;
        }
        if (field === 'status' && ['new', 'in_progress', 'resolved', 'closed', 'reopened'].includes(value)) {
            const preview = document.createElement('span');
            preview.className = `ancore-custom-select__preview status-indicator status-${value} tasks-filter-status-icon`;
            preview.setAttribute('aria-hidden', 'true');
            return preview;
        }
        const fieldIcons = {
            assignee: 'user-round', assigned_to: 'user-round', responsible_user: 'user-round', shared_with: 'users',
            space: 'layers', team: 'users', tags: 'tag', tag: 'tag',
            work_type: 'shapes', type: 'shapes',
            sort: 'arrow-up-down', visibility: 'users', kind: 'layers',
            management: 'building-2', configuration: 'settings', sprint: 'timer', epic: 'zap',
        };
        const values = {
            visibility: { private: 'lock', public: 'users', selected: 'users', workspace: 'building-2' },
            kind: { software: 'code', business: 'briefcase', service: 'headset', equipment: 'monitor', license: 'key-round', tool: 'wrench' },
            management: { team: 'users', company: 'building-2' },
        };
        const name = option?.dataset.ancoreOptionIcon || values[field]?.[value]
            || select?.dataset.ancoreCustomSelectIcon || fieldIcons[field] || 'list';
        return name ? window.AncoreIcons?.create(name, { className: 'ancore-custom-select__icon' }) : null;
    }

    function buildOption(select, option, index) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'ancore-custom-select__option';
        button.setAttribute('role', 'option');
        button.setAttribute('data-ancore-custom-select-option', '');
        button.dataset.optionIndex = String(index);
        button.disabled = option.disabled;

        const check = document.createElement('span');
        check.className = 'ancore-custom-select__check';
        check.setAttribute('aria-hidden', 'true');

        const label = document.createElement('span');
        label.className = 'ancore-custom-select__option-label';
        label.textContent = option.textContent.trim() || option.value || 'Opcja';
        button.title = label.textContent;

        button.append(check);
        const visual = optionVisual(option, select);
        if (visual) button.append(visual);
        button.append(label);
        button.setAttribute('aria-selected', option.selected ? 'true' : 'false');
        button.classList.toggle('is-selected', option.selected);

        if (select.multiple) {
            button.setAttribute('aria-checked', option.selected ? 'true' : 'false');
        }

        return button;
    }

    function rebuildMenu(wrapper) {
        const { select, list } = getWrapperParts(wrapper);
        if (!select || !list) return;

        list.textContent = '';

        let currentGroup = null;
        Array.from(select.options).forEach((option, index) => {
            const group = option.parentElement?.tagName === 'OPTGROUP' ? option.parentElement : null;
            if (group && group !== currentGroup) {
                currentGroup = group;
                const groupLabel = document.createElement('span');
                groupLabel.className = 'ancore-custom-select__group-label';
                groupLabel.textContent = group.label;
                list.appendChild(groupLabel);
            } else if (!group) {
                currentGroup = null;
            }

            list.appendChild(buildOption(select, option, index));
        });

        const empty = document.createElement('span');
        empty.className = 'ancore-custom-select__empty';
        empty.setAttribute('data-ancore-custom-select-empty', '');
        empty.hidden = true;
        empty.textContent = 'Brak wyników';
        list.appendChild(empty);

        renderIcon(list);
        filterOptions(wrapper);
    }

    function syncWrapper(wrapper) {
        const { select, button, label, menu } = getWrapperParts(wrapper);
        if (!select || !button || !label || !menu) return;

        label.textContent = selectedLabel(select);
        button.querySelector('.ancore-custom-select__icon, .ancore-custom-select__preview')?.remove();
        const icon = select.getAttribute('data-ancore-custom-select-icon');
        const plain = select.name === 'task_type' || select.name === 'task_group';
        const visual = plain ? null : (select.selectedOptions.length === 1 ? optionVisual(select.selectedOptions[0], select) : null)
            || window.AncoreIcons?.create(icon || 'list-filter', { className: 'ancore-custom-select__icon' });
        if (visual) {
            button.prepend(visual);
            renderIcon(button);
        }
        button.disabled = select.disabled;
        button.setAttribute('aria-disabled', select.disabled ? 'true' : 'false');
        wrapper.classList.toggle('is-disabled', select.disabled);
        wrapper.classList.toggle('is-multiple', select.multiple);

        Array.from(menu.querySelectorAll(OPTION_SELECTOR)).forEach(optionButton => {
            const option = select.options[Number(optionButton.dataset.optionIndex)];
            const selected = Boolean(option?.selected);
            optionButton.classList.toggle('is-selected', selected);
            optionButton.setAttribute('aria-selected', selected ? 'true' : 'false');
            if (select.multiple) {
                optionButton.setAttribute('aria-checked', selected ? 'true' : 'false');
            } else {
                optionButton.removeAttribute('aria-checked');
            }
            optionButton.disabled = Boolean(option?.disabled);
        });
    }

    function refreshWrapper(wrapper) {
        if (!wrapper) return;
        rebuildMenu(wrapper);
        syncWrapper(wrapper);
    }

    function closeWrapper(wrapper, restoreFocus = false) {
        if (!wrapper) return;
        const { button, menu } = getWrapperParts(wrapper);
        window.AncoreDropdownLayer?.hide(menu);
        wrapper.classList.remove('is-open');
        button?.setAttribute('aria-expanded', 'false');
        if (menu) menu.hidden = true;
        resetSearch(wrapper);
        if (restoreFocus) button?.focus({ preventScroll: true });
    }

    function closeAll(except = null) {
        document.querySelectorAll(`${WRAPPER_SELECTOR}.is-open`).forEach(wrapper => {
            if (wrapper !== except) closeWrapper(wrapper);
        });
    }

    function selectedOptionButton(wrapper) {
        const options = optionButtons(wrapper);
        return options.find(optionButton => optionButton.classList.contains('is-selected'))
            || options[0]
            || wrapper.querySelector(`${OPTION_SELECTOR}.is-selected:not(:disabled)`)
            || wrapper.querySelector(`${OPTION_SELECTOR}:not(:disabled)`);
    }

    function openWrapper(wrapper, focusSelected = false) {
        const { select, button, menu, search } = getWrapperParts(wrapper);
        if (!select || !button || !menu || select.disabled) return;

        closeAll(wrapper);
        refreshWrapper(wrapper);
        wrapper.classList.add('is-open');
        button.setAttribute('aria-expanded', 'true');
        menu.hidden = false;

        window.AncoreDropdownLayer?.open(menu, button, () => closeWrapper(wrapper));

        if (focusSelected) {
            selectedOptionButton(wrapper)?.focus({ preventScroll: true });
        } else if (search) {
            search.focus({ preventScroll: true });
        }
    }

    function chooseOption(optionButton) {
        const wrapper = optionButton.closest(WRAPPER_SELECTOR);
        const { select } = getWrapperParts(wrapper);
        const option = select?.options[Number(optionButton.dataset.optionIndex)];
        if (!wrapper || !select || !option || option.disabled) return;

        if (select.multiple) {
            option.selected = !option.selected;
            syncWrapper(wrapper);
        } else {
            select.selectedIndex = Number(optionButton.dataset.optionIndex);
            syncWrapper(wrapper);
            closeWrapper(wrapper, true);
        }

        select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function chooseCustomValue(wrapper) {
        const { select, search } = getWrapperParts(wrapper);
        if (select?.dataset.ancoreCustomSelectAllowCustom !== 'true' || select.disabled || !search) return;
        const value = search.value.trim();
        if (!value || !search.checkValidity()) return;
        let option = Array.from(select.options).find(option => option.value === value);
        if (!option) {
            option = new Option(value, value);
            select.add(option);
        }
        if (option.disabled) return;
        select.value = option.value;
        refreshWrapper(wrapper);
        closeWrapper(wrapper, true);
        select.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function focusOption(wrapper, direction) {
        const options = optionButtons(wrapper);
        if (!options.length) return;

        if (!wrapper.classList.contains('is-open')) {
            openWrapper(wrapper);
        }

        const focusedIndex = options.indexOf(document.activeElement);
        const selectedIndex = options.indexOf(selectedOptionButton(wrapper));
        const currentIndex = focusedIndex >= 0 ? focusedIndex : Math.max(0, selectedIndex);
        const inSearch = document.activeElement?.matches(SEARCH_INPUT_SELECTOR);
        const nextIndex = inSearch ? (direction > 0 ? 0 : options.length - 1)
            : (currentIndex + direction + options.length) % options.length;
        options[nextIndex]?.focus({ preventScroll: true });
        options[nextIndex]?.scrollIntoView({ block: 'nearest' });
    }

    function enhanceSelect(select) {
        if (!shouldEnhance(select)) return null;

        const wrapper = document.createElement('div');
        wrapper.className = 'ancore-custom-select';
        wrapper.setAttribute('data-ancore-custom-select', '');
        wrapper.classList.toggle('ancore-custom-select--inline', select.classList.contains('tasks-inline-select'));
        wrapper.classList.toggle('ancore-custom-select--form', select.classList.contains('form-input') || select.classList.contains('form-select'));

        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'ancore-custom-select__button';
        button.setAttribute('aria-haspopup', 'listbox');
        button.setAttribute('aria-expanded', 'false');
        button.setAttribute('data-ancore-custom-select-toggle', '');

        const label = document.createElement('span');
        label.className = 'ancore-custom-select__label';
        label.setAttribute('data-ancore-custom-select-label', '');
        label.id = nextId('ancore-custom-select-label');

        const caret = document.createElement('i');
        caret.className = 'ancore-custom-select__caret';
        caret.setAttribute('data-icon', 'chevron-down');
        caret.setAttribute('aria-hidden', 'true');

        button.append(label, caret);

        const menu = document.createElement('div');
        menu.className = 'ancore-custom-select__menu';
        menu.setAttribute('data-ancore-custom-select-menu', '');
        menu.hidden = true;

        if (select.hasAttribute(SEARCH_ATTR) || select.multiple || select.options.length > 8 || select.closest('.tasks-modal, .profile-edit-dialog')) {
            const searchWrap = document.createElement('div');
            searchWrap.className = 'ancore-custom-select__search';

            const searchIcon = document.createElement('i');
            searchIcon.setAttribute('data-icon', 'search');
            searchIcon.setAttribute('aria-hidden', 'true');

            const search = document.createElement('input');
            search.type = 'search';
            search.className = 'ancore-custom-select__search-input';
            search.placeholder = select.getAttribute('data-ancore-custom-select-search-placeholder') || 'Szukaj';
            search.autocomplete = 'off';
            search.spellcheck = false;
            search.setAttribute('aria-label', `Szukaj: ${getLabelText(select)}`);
            search.setAttribute('data-ancore-custom-select-search-input', '');
            if (select.dataset.ancoreCustomSelectAllowCustom === 'true') {
                search.setAttribute('aria-label', 'Wpisz własne źródło lub wyszukaj na liście');
                const maxLength = Number(select.dataset.ancoreCustomSelectMaxLength);
                if (Number.isInteger(maxLength) && maxLength > 0) search.maxLength = maxLength;
            }

            searchWrap.append(searchIcon, search);
            menu.appendChild(searchWrap);
        }

        if (select.dataset.ancoreCustomSelectAllowCustom === 'true') {
            const customOption = document.createElement('button');
            customOption.type = 'button';
            customOption.className = 'ancore-custom-select__option ancore-custom-select__custom-option';
            customOption.setAttribute('data-ancore-custom-select-custom-option', '');
            customOption.hidden = true;
            menu.appendChild(customOption);
        }

        const list = document.createElement('div');
        list.className = 'ancore-custom-select__list';
        list.setAttribute('role', 'listbox');
        list.setAttribute('data-ancore-custom-select-list', '');
        if (select.multiple) {
            list.setAttribute('aria-multiselectable', 'true');
        }
        menu.appendChild(list);

        const labelElement = select.labels?.[0];
        const labelId = ensureElementId(labelElement, 'ancore-custom-select-field');
        if (labelId) {
            button.setAttribute('aria-labelledby', `${labelId} ${label.id}`);
            list.setAttribute('aria-labelledby', labelId);
        } else {
            const fallbackLabel = getLabelText(select);
            button.setAttribute('aria-label', fallbackLabel);
            list.setAttribute('aria-label', fallbackLabel);
        }

        select.parentNode.insertBefore(wrapper, select);
        wrapper.append(select, button, menu);
        select.setAttribute(SOURCE_ATTR, 'true');
        select.classList.add('ancore-custom-select__source');
        if (!select.dataset.ancoreOriginalTabindex) {
            select.dataset.ancoreOriginalTabindex = select.getAttribute('tabindex') || '';
        }
        select.tabIndex = -1;
        select.setAttribute('aria-hidden', 'true');

        refreshWrapper(wrapper);
        renderIcon(wrapper);
        return wrapper;
    }

    function init(scope = document) {
        const root = scope instanceof Element || scope instanceof Document ? scope : document;
        root.querySelectorAll('select').forEach(enhanceSelect);
    }

    function refresh(scope = document) {
        const root = scope instanceof Element || scope instanceof Document ? scope : document;
        if (root.matches?.(WRAPPER_SELECTOR)) {
            refreshWrapper(root);
        }
        root.querySelectorAll?.(WRAPPER_SELECTOR).forEach(refreshWrapper);
        init(root);
    }

    function scheduleRefresh(scope = document) {
        window.clearTimeout(refreshTimer);
        refreshTimer = window.setTimeout(() => refresh(scope), 0);
    }

    document.addEventListener('click', event => {
        const target = event.target instanceof Element ? event.target : event.target?.parentElement;
        const toggle = target?.closest('[data-ancore-custom-select-toggle]');
        const option = target?.closest(OPTION_SELECTOR);
        const customOption = target?.closest(CUSTOM_OPTION_SELECTOR);

        if (customOption) {
            chooseCustomValue(customOption.closest(WRAPPER_SELECTOR));
            return;
        }

        if (toggle) {
            const wrapper = toggle.closest(WRAPPER_SELECTOR);
            if (wrapper.classList.contains('is-open')) {
                closeWrapper(wrapper);
            } else {
                openWrapper(wrapper);
            }
            return;
        }

        if (option) {
            chooseOption(option);
            return;
        }

        if (!target?.closest(WRAPPER_SELECTOR)) {
            closeAll();
            scheduleRefresh();
        }
    });

    document.addEventListener('keydown', event => {
        const target = event.target instanceof Element ? event.target : event.target?.parentElement;
        const wrapper = target?.closest(WRAPPER_SELECTOR);
        if (!wrapper) return;

        if (event.key === 'Enter' && target.matches(SEARCH_INPUT_SELECTOR)) {
            if (event.isComposing) return;
            event.preventDefault();
            if (getWrapperParts(wrapper).select?.dataset.ancoreCustomSelectAllowCustom === 'true') {
                chooseCustomValue(wrapper);
            } else {
                const first = optionButtons(wrapper)[0];
                if (first) chooseOption(first);
            }
            return;
        }

        if (event.key === 'Escape' && wrapper.classList.contains('is-open')) {
            event.preventDefault();
            event.stopPropagation();
            closeWrapper(wrapper, true);
            return;
        }

        if (event.key === 'ArrowDown') {
            event.preventDefault();
            focusOption(wrapper, 1);
            return;
        }

        if (event.key === 'ArrowUp') {
            event.preventDefault();
            focusOption(wrapper, -1);
            return;
        }

        if ((event.key === 'Enter' || event.key === ' ') && target.matches(OPTION_SELECTOR)) {
            event.preventDefault();
            chooseOption(target);
            return;
        }

        if ((event.key === 'Enter' || event.key === ' ') && target.matches('[data-ancore-custom-select-toggle]')) {
            event.preventDefault();
            openWrapper(wrapper, true);
        }
    }, true);

    document.addEventListener('change', event => {
        const select = event.target instanceof HTMLSelectElement ? event.target : null;
        const wrapper = wrapperForSelect(select);
        if (wrapper) {
            wrapper.classList.remove('is-invalid');
            syncWrapper(wrapper);
        }
    });

    document.addEventListener('reset', event => {
        const form = event.target instanceof HTMLFormElement ? event.target : null;
        if (form) window.setTimeout(() => refresh(form), 0);
    });

    document.addEventListener('invalid', event => {
        const select = event.target instanceof HTMLSelectElement ? event.target : null;
        const wrapper = wrapperForSelect(select);
        if (!wrapper) return;

        wrapper.classList.add('is-invalid');
        getWrapperParts(wrapper).button?.focus({ preventScroll: true });
    }, true);

    document.addEventListener('input', event => {
        const target = event.target instanceof Element ? event.target : null;
        if (target?.matches(SEARCH_INPUT_SELECTOR)) {
            const wrapper = target.closest(WRAPPER_SELECTOR);
            if (wrapper) filterOptions(wrapper);
            return;
        }

        const select = event.target instanceof HTMLSelectElement ? event.target : null;
        const wrapper = wrapperForSelect(select);
        if (wrapper) wrapper.classList.remove('is-invalid');
    });

    document.addEventListener('ancore:content-loaded', () => refresh(document));
    document.addEventListener('DOMContentLoaded', () => init(document));

    if (document.readyState !== 'loading') {
        init(document);
    }

    window.AncoreCustomSelect = {
        init,
        refresh,
        closeAll
    };
})();
