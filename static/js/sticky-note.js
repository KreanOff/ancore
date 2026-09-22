(function () {
    const initializedNotes = new WeakSet();
    const DEFAULT_TEXT = '';
    const DEFAULT_OPEN = false;
    const EDGE_GAP = 8;
    const MIN_WIDTH = 180;
    const MIN_HEIGHT = 140;

    function readState(storageKey) {
        try {
            // The old v1 note has no owner: never assign it to the next login.
            const parsed = JSON.parse(window.localStorage.getItem(storageKey) || '{}');
            return {
                open: typeof parsed.open === 'boolean' ? parsed.open : DEFAULT_OPEN,
                left: Number.isFinite(parsed.left) ? parsed.left : null,
                top: Number.isFinite(parsed.top) ? parsed.top : null,
                width: Number.isFinite(parsed.width) ? parsed.width : null,
                height: Number.isFinite(parsed.height) ? parsed.height : null,
                text: typeof parsed.text === 'string' ? parsed.text : DEFAULT_TEXT,
            };
        } catch (error) {
            return {
                open: DEFAULT_OPEN,
                left: null,
                top: null,
                width: null,
                height: null,
                text: DEFAULT_TEXT,
            };
        }
    }

    function persistState(storageKey, state) {
        try {
            window.localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (error) {
            // localStorage can be disabled; the sticker should still work for this page view.
        }
    }

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function defaultLeft(note) {
        const sidebarWidth = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width')) || 56;
        const width = note.offsetWidth || defaultWidth();
        return Math.min(window.innerWidth - width - EDGE_GAP, sidebarWidth + 24);
    }

    function defaultTop() {
        return 92;
    }

    function defaultWidth() {
        return Math.min(280, window.innerWidth - EDGE_GAP * 2);
    }

    function defaultHeight() {
        return Math.min(220, window.innerHeight - EDGE_GAP * 2);
    }

    function clampSize(width, height, left, top) {
        const maxWidth = Math.max(MIN_WIDTH, window.innerWidth - (left ?? EDGE_GAP) - EDGE_GAP);
        const maxHeight = Math.max(MIN_HEIGHT, window.innerHeight - (top ?? EDGE_GAP) - EDGE_GAP);
        return {
            width: clamp(width, MIN_WIDTH, maxWidth),
            height: clamp(height, MIN_HEIGHT, maxHeight),
        };
    }

    function clampPosition(note, left, top, width, height) {
        const actualWidth = width ?? note.offsetWidth;
        const actualHeight = height ?? note.offsetHeight;
        const maxLeft = Math.max(EDGE_GAP, window.innerWidth - actualWidth - EDGE_GAP);
        const maxTop = Math.max(EDGE_GAP, window.innerHeight - actualHeight - EDGE_GAP);
        return {
            left: clamp(left, EDGE_GAP, maxLeft),
            top: clamp(top, EDGE_GAP, maxTop),
        };
    }

    function isInteractiveTarget(target) {
        return Boolean(target?.closest?.('button, textarea, input, select, a, [data-sticky-note-resize]'));
    }

    function bootStickyNote() {
        const note = document.querySelector('[data-sticky-note]');
        const toggle = document.querySelector('[data-sticky-note-toggle]');
        const handle = note?.querySelector('[data-sticky-note-handle]');
        const closeButton = note?.querySelector('[data-sticky-note-close]');
        const textInput = note?.querySelector('[data-sticky-note-text]');
        const resizeHandle = note?.querySelector('[data-sticky-note-resize]');

        if (!note || !toggle || !handle || !closeButton || !textInput || !resizeHandle
            || !note.dataset.stickyNoteUser || initializedNotes.has(note)) {
            return;
        }
        initializedNotes.add(note);

        const storageKey = `ancore:sticky-note:v2:user:${note.dataset.stickyNoteUser}`;
        const state = readState(storageKey);
        const saveState = (nextState) => persistState(storageKey, nextState);

        function applyToggleState() {
            const isOpen = !note.hidden;
            toggle.classList.toggle('is-open', isOpen);
            toggle.setAttribute('aria-expanded', String(isOpen));
        }

        function applyGeometry() {
            const size = clampSize(
                state.width ?? defaultWidth(),
                state.height ?? defaultHeight(),
                state.left ?? defaultLeft(note),
                state.top ?? defaultTop()
            );
            state.width = size.width;
            state.height = size.height;
            note.style.width = `${size.width}px`;
            note.style.height = `${size.height}px`;

            const position = clampPosition(
                note,
                state.left ?? defaultLeft(note),
                state.top ?? defaultTop(),
                size.width,
                size.height
            );
            state.left = position.left;
            state.top = position.top;
            note.style.left = `${position.left}px`;
            note.style.top = `${position.top}px`;
        }

        function setOpen(nextOpen) {
            note.hidden = !nextOpen;
            state.open = nextOpen;
            applyToggleState();
            saveState(state);

            if (nextOpen) {
                window.requestAnimationFrame(function () {
                    applyGeometry();
                    window.AncoreIcons?.render(note);
                    textInput.focus({ preventScroll: true });
                });
            }
        }

        textInput.value = state.text;
        setOpen(state.open);

        toggle.addEventListener('click', function () {
            setOpen(note.hidden);
        });

        closeButton.addEventListener('pointerdown', function (event) {
            event.stopPropagation();
        });

        closeButton.addEventListener('click', function (event) {
            event.preventDefault();
            event.stopPropagation();
            setOpen(false);
        });

        textInput.addEventListener('input', function () {
            state.text = textInput.value;
            saveState(state);
        });

        handle.addEventListener('pointerdown', function (event) {
            if (event.button !== 0 && event.pointerType !== 'touch') {
                return;
            }

            if (isInteractiveTarget(event.target)) {
                return;
            }

            const startX = event.clientX;
            const startY = event.clientY;
            const startLeft = state.left ?? note.getBoundingClientRect().left;
            const startTop = state.top ?? note.getBoundingClientRect().top;

            handle.setPointerCapture?.(event.pointerId);
            document.body.classList.add('app-sticky-note-dragging');

            function move(moveEvent) {
                const next = clampPosition(
                    note,
                    startLeft + moveEvent.clientX - startX,
                    startTop + moveEvent.clientY - startY,
                    state.width ?? note.offsetWidth,
                    state.height ?? note.offsetHeight
                );
                state.left = next.left;
                state.top = next.top;
                note.style.left = `${next.left}px`;
                note.style.top = `${next.top}px`;
            }

            function stop() {
                handle.releasePointerCapture?.(event.pointerId);
                document.body.classList.remove('app-sticky-note-dragging');
                saveState(state);
                window.removeEventListener('pointermove', move);
                window.removeEventListener('pointerup', stop);
                window.removeEventListener('pointercancel', stop);
            }

            window.addEventListener('pointermove', move);
            window.addEventListener('pointerup', stop);
            window.addEventListener('pointercancel', stop);
        });

        resizeHandle.addEventListener('pointerdown', function (event) {
            if (event.button !== 0 && event.pointerType !== 'touch') {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            const startX = event.clientX;
            const startY = event.clientY;
            const startWidth = state.width ?? note.offsetWidth;
            const startHeight = state.height ?? note.offsetHeight;
            const left = state.left ?? note.getBoundingClientRect().left;
            const top = state.top ?? note.getBoundingClientRect().top;

            resizeHandle.setPointerCapture?.(event.pointerId);
            document.body.classList.add('app-sticky-note-resizing');

            function move(moveEvent) {
                const next = clampSize(
                    startWidth + moveEvent.clientX - startX,
                    startHeight + moveEvent.clientY - startY,
                    left,
                    top
                );
                state.width = next.width;
                state.height = next.height;
                note.style.width = `${next.width}px`;
                note.style.height = `${next.height}px`;
            }

            function stop() {
                resizeHandle.releasePointerCapture?.(event.pointerId);
                document.body.classList.remove('app-sticky-note-resizing');
                applyGeometry();
                saveState(state);
                window.removeEventListener('pointermove', move);
                window.removeEventListener('pointerup', stop);
                window.removeEventListener('pointercancel', stop);
            }

            window.addEventListener('pointermove', move);
            window.addEventListener('pointerup', stop);
            window.addEventListener('pointercancel', stop);
        });

        resizeHandle.addEventListener('keydown', function (event) {
            const step = event.shiftKey ? 40 : 12;
            let widthDelta = 0;
            let heightDelta = 0;

            if (event.key === 'ArrowRight') widthDelta = step;
            if (event.key === 'ArrowLeft') widthDelta = -step;
            if (event.key === 'ArrowDown') heightDelta = step;
            if (event.key === 'ArrowUp') heightDelta = -step;

            if (!widthDelta && !heightDelta) {
                return;
            }

            event.preventDefault();

            const next = clampSize(
                (state.width ?? note.offsetWidth) + widthDelta,
                (state.height ?? note.offsetHeight) + heightDelta,
                state.left ?? note.getBoundingClientRect().left,
                state.top ?? note.getBoundingClientRect().top
            );
            state.width = next.width;
            state.height = next.height;
            note.style.width = `${next.width}px`;
            note.style.height = `${next.height}px`;
            applyGeometry();
            saveState(state);
        });

        window.addEventListener('resize', function () {
            if (!note.hidden) {
                applyGeometry();
                saveState(state);
            }
        });

        document.addEventListener('ancore:content-loaded', applyToggleState);
    }

    document.addEventListener('ancore:content-loaded', bootStickyNote);
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bootStickyNote, { once: true });
    } else {
        bootStickyNote();
    }
})();
