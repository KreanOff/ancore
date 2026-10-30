(function () {
    if (window.AncoreFieldHelp) return;
    let active = null;
    let closeTimer = null;
    let suppressedFocus = null;

    function clearTimer() {
        clearTimeout(closeTimer);
        closeTimer = null;
    }

    function closed(current) {
        clearTimer();
        current.content.hidden = true;
        current.anchor.setAttribute('aria-expanded', 'false');
        if (active === current) active = null;
        // The shared layer restores focus after Escape. Do not reopen on that focus.
        suppressedFocus = current.anchor;
        queueMicrotask(() => { suppressedFocus = null; });
    }

    function close() {
        if (!active) return;
        const current = active;
        window.AncoreDropdownLayer?.hide(current.content);
        closed(current);
    }

    function open(wrapper) {
        clearTimer();
        if (active?.wrapper === wrapper) return;
        const anchor = wrapper.querySelector('[data-field-help-toggle]');
        const content = wrapper.querySelector('[data-field-help-content]');
        if (!anchor || anchor.disabled || !content) return;
        close();
        const current = { wrapper, anchor, content, pinned: false };
        active = current;
        content.hidden = false;
        anchor.setAttribute('aria-expanded', 'true');
        window.AncoreDropdownLayer?.open(content, anchor, () => closed(current));
    }

    function leave(wrapper) {
        clearTimer();
        const current = active;
        if (!current || current.wrapper !== wrapper) return;
        // Allow moving through the small gap between the marker and its bubble.
        closeTimer = setTimeout(() => {
            if (active === current && !current.pinned && !wrapper.matches(':hover')
                && !wrapper.contains(document.activeElement)) close();
        }, 120);
    }

    document.addEventListener('pointerover', event => {
        if (event.pointerType === 'touch') return;
        const wrapper = event.target.closest?.('[data-field-help]');
        if (wrapper) open(wrapper);
    });
    document.addEventListener('pointerout', event => {
        const wrapper = event.target.closest?.('[data-field-help]');
        if (wrapper && !wrapper.contains(event.relatedTarget)) leave(wrapper);
    });
    document.addEventListener('focusin', event => {
        const wrapper = event.target.closest?.('[data-field-help]');
        if (wrapper && event.target !== suppressedFocus) open(wrapper);
        else if (!wrapper) close();
    });
    document.addEventListener('focusout', event => {
        const wrapper = event.target.closest?.('[data-field-help]');
        if (wrapper && !wrapper.contains(event.relatedTarget)) leave(wrapper);
    });
    document.addEventListener('click', event => {
        const anchor = event.target.closest?.('[data-field-help-toggle]');
        if (!anchor) return;
        event.preventDefault();
        const wrapper = anchor.closest('[data-field-help]');
        if (active?.wrapper === wrapper && active.pinned) close();
        else {
            open(wrapper);
            if (active?.wrapper === wrapper) active.pinned = true;
        }
    });
    document.addEventListener('pointerdown', event => {
        if (active && !active.wrapper.contains(event.target)) close();
    }, true);
    // The layer handles Escape first when popovers are supported; this also
    // dismisses the positioned fallback before the parent dialog handles Escape.
    window.addEventListener('keydown', event => {
        if (event.key !== 'Escape' || !active) return;
        event.preventDefault();
        event.stopImmediatePropagation();
        const anchor = active.anchor;
        close();
        anchor.focus({ preventScroll: true });
    }, true);
    document.addEventListener('ancore:content-loaded', close);
    window.addEventListener('pagehide', close);
    window.AncoreFieldHelp = { close };
})();
