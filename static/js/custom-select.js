(function () {
    const WRAPPER_SELECTOR = '[data-ancore-custom-select]';
    const SOURCE_ATTR = 'data-ancore-custom-select-source';
    const OPTION_SELECTOR = '[data-ancore-custom-select-option]';
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
            if (!selected.length) return 'Wybierz opcje';
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
            menu: wrapper.querySelector('[data-ancore-custom-select-menu]')
        };
    }

    function renderIcon(scope) {
        if (window.AncoreIcons?.render) {
            window.AncoreIcons.render(scope);
        } else if (window.lucide?.createIcons) {
            window.lucide.createIcons();
        }
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

        button.append(check, label);
        button.setAttribute('aria-selected', option.selected ? 'true' : 'false');
        button.classList.toggle('is-selected', option.selected);

        if (select.multiple) {
            button.setAttribute('aria-checked', option.selected ? 'true' : 'false');
        }

        return button;
    }

    function rebuildMenu(wrapper) {
        const { select, menu } = getWrapperParts(wrapper);
        if (!select || !menu) return;

        menu.textContent = '';

        let currentGroup = null;
        Array.from(select.options).forEach((option, index) => {
            const group = option.parentElement?.tagName === 'OPTGROUP' ? option.parentElement : null;
            if (group && group !== currentGroup) {
                currentGroup = group;
                const groupLabel = document.createElement('span');
                groupLabel.className = 'ancore-custom-select__group-label';
                groupLabel.textContent = group.label;
                menu.appendChild(groupLabel);
            } else if (!group) {
                currentGroup = null;
            }

            menu.appendChild(buildOption(select, option, index));
        });
    }

    function syncWrapper(wrapper) {
        const { select, button, label, menu } = getWrapperParts(wrapper);
        if (!select || !button || !label || !menu) return;

        label.textContent = selectedLabel(select);
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
        wrapper.classList.remove('is-open');
        button?.setAttribute('aria-expanded', 'false');
        if (menu) menu.hidden = true;
        if (restoreFocus) button?.focus({ preventScroll: true });
    }

    function closeAll(except = null) {
        document.querySelectorAll(`${WRAPPER_SELECTOR}.is-open`).forEach(wrapper => {
            if (wrapper !== except) closeWrapper(wrapper);
        });
    }

    function selectedOptionButton(wrapper) {
        return wrapper.querySelector(`${OPTION_SELECTOR}.is-selected:not(:disabled)`)
            || wrapper.querySelector(`${OPTION_SELECTOR}:not(:disabled)`);
    }

    function openWrapper(wrapper, focusSelected = false) {
        const { select, button, menu } = getWrapperParts(wrapper);
        if (!select || !button || !menu || select.disabled) return;

        closeAll(wrapper);
        refreshWrapper(wrapper);
        wrapper.classList.add('is-open');
        button.setAttribute('aria-expanded', 'true');
        menu.hidden = false;

        if (focusSelected) {
            selectedOptionButton(wrapper)?.focus({ preventScroll: true });
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

    function focusOption(wrapper, direction) {
        const options = Array.from(wrapper.querySelectorAll(`${OPTION_SELECTOR}:not(:disabled)`));
        if (!options.length) return;

        if (!wrapper.classList.contains('is-open')) {
            openWrapper(wrapper);
        }

        const focusedIndex = options.indexOf(document.activeElement);
        const selectedIndex = options.indexOf(selectedOptionButton(wrapper));
        const currentIndex = focusedIndex >= 0 ? focusedIndex : Math.max(0, selectedIndex);
        const nextIndex = (currentIndex + direction + options.length) % options.length;
        options[nextIndex]?.focus({ preventScroll: true });
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
        caret.setAttribute('data-lucide', 'chevron-down');
        caret.setAttribute('aria-hidden', 'true');

        button.append(label, caret);

        const menu = document.createElement('div');
        menu.className = 'ancore-custom-select__menu';
        menu.setAttribute('role', 'listbox');
        menu.setAttribute('data-ancore-custom-select-menu', '');
        menu.hidden = true;
        if (select.multiple) {
            menu.setAttribute('aria-multiselectable', 'true');
        }

        const labelElement = select.labels?.[0];
        const labelId = ensureElementId(labelElement, 'ancore-custom-select-field');
        if (labelId) {
            button.setAttribute('aria-labelledby', `${labelId} ${label.id}`);
            menu.setAttribute('aria-labelledby', labelId);
        } else {
            const fallbackLabel = getLabelText(select);
            button.setAttribute('aria-label', fallbackLabel);
            menu.setAttribute('aria-label', fallbackLabel);
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

        if (event.key === 'Escape') {
            event.preventDefault();
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
    });

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
