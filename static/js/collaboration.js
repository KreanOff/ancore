(() => {
    if (window.AncoreCollaboration) return;
    window.AncoreCollaboration = true;
    let controller;

    function init() {
        controller?.abort();
        controller = new AbortController();
        const { signal } = controller;

        document.querySelectorAll('[data-follow-url]').forEach(button => {
            button.addEventListener('click', async () => {
                const following = button.getAttribute('aria-pressed') !== 'true';
                button.disabled = true;
                try {
                    const response = await fetch(button.dataset.followUrl, {
                        method: 'POST', signal,
                        headers: { 'X-CSRFToken': button.dataset.followCsrf, 'X-Requested-With': 'XMLHttpRequest' },
                        body: new URLSearchParams({ following: String(following) }),
                    });
                    if (!response.ok) throw new Error();
                    const data = await response.json();
                    button.setAttribute('aria-pressed', String(data.following));
                    button.querySelector('[data-follow-label]').textContent = data.following ? 'Obserwujesz' : 'Obserwuj';
                    window.showNotification?.(data.following ? 'Obserwowanie włączone.' : 'Obserwowanie wyłączone.', 'success');
                } catch (error) {
                    if (error.name !== 'AbortError') window.showNotification?.('Nie udało się zmienić obserwowania. Spróbuj ponownie.', 'error');
                } finally {
                    button.disabled = false;
                }
            }, { signal });
        });

        const composer = document.querySelector('[data-mention-composer]');
        if (!composer) return;
        const input = composer.querySelector('[data-mention-input]');
        const menu = composer.querySelector('[data-mention-menu]');
        const status = composer.querySelector('[data-mention-status]');
        const people = JSON.parse(document.getElementById('mention-people').textContent);
        const mentionValues = input.form.querySelector('[data-mention-values]');
        let previousValue = input.value;
        // Keep the chosen account attached to its visible text while the user edits.
        const initialMentions = JSON.parse(mentionValues.value || '[]');
        let mentions = initialMentions.map(entry => ({
            ...entry,
            start: Array.from(input.value).slice(0, entry.start).join('').length,
            end: Array.from(input.value).slice(0, entry.end).join('').length,
        }));
        let matches = [], selected = 0, start = 0;

        function saveMentions() {
            mentionValues.value = JSON.stringify(mentions.map(entry => ({
                user_id: entry.user_id,
                start: Array.from(input.value.slice(0, entry.start)).length,
                end: Array.from(input.value.slice(0, entry.end)).length,
            })));
        }

        function syncMentions() {
            const current = input.value;
            if (current === previousValue) return;
            let prefix = 0, oldEnd = previousValue.length, newEnd = current.length;
            while (prefix < oldEnd && prefix < newEnd && previousValue[prefix] === current[prefix]) prefix++;
            while (oldEnd > prefix && newEnd > prefix && previousValue[oldEnd - 1] === current[newEnd - 1]) {
                oldEnd--; newEnd--;
            }
            const shift = newEnd - oldEnd;
            mentions = mentions.flatMap(entry => {
                if (entry.end <= prefix) return [entry];
                if (entry.start >= oldEnd) return [{ ...entry, start: entry.start + shift, end: entry.end + shift }];
                return [];
            });
            previousValue = current;
            saveMentions();
        }

        function close() {
            menu.hidden = true;
            status.textContent = '';
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
        }

        function select(index) {
            selected = index;
            menu.querySelectorAll('[role="option"]').forEach((option, i) => {
                option.setAttribute('aria-selected', String(i === selected));
                option.classList.toggle('is-active', i === selected);
                if (i === selected) {
                    input.setAttribute('aria-activedescendant', option.id);
                    option.scrollIntoView({ block: 'nearest' });
                }
            });
        }

        function insert(person) {
            const mentionStart = start;
            input.setRangeText(`${person.mention} `, start, input.selectionStart, 'end');
            syncMentions();
            mentions.push({ user_id: person.id, start: mentionStart, end: mentionStart + person.mention.length });
            saveMentions();
            close();
            input.focus();
            input.dispatchEvent(new Event('input', { bubbles: true }));
        }

        function update() {
            syncMentions();
            if (input.selectionStart !== input.selectionEnd) return close();
            const before = input.value.slice(0, input.selectionStart);
            const match = before.match(/(?:^|[^\p{L}\p{N}_@.+-])@([\p{L}\p{N}_@.+'’-]*(?: +[\p{L}\p{N}_.+'’-]*)*)$/u);
            if (!match) return close();
            start = before.length - match[1].length - 1;
            if (mentions.some(entry => start >= entry.start && start < entry.end)) return close();
            const query = match[1].trim().toLocaleLowerCase('pl');
            if (!/[\p{L}\p{N}]/u.test(query)) {
                matches = [];
                menu.replaceChildren();
                return close();
            }
            matches = people.filter(person => `${person.label} ${person.email}`.toLocaleLowerCase('pl').includes(query)).slice(0, 8);
            menu.replaceChildren();
            matches.forEach((person, index) => {
                const option = document.createElement('button');
                option.type = 'button';
                option.role = 'option';
                option.id = `mention-person-${index}`;
                option.textContent = `${person.label} · ${person.email}`;
                option.tabIndex = -1;
                option.addEventListener('mousedown', event => event.preventDefault());
                option.addEventListener('click', () => insert(person));
                menu.append(option);
            });
            if (!matches.length) {
                const empty = document.createElement('p');
                empty.className = 'tasks-filter-menu-empty';
                empty.textContent = 'Brak pasujących osób w Workspace.';
                menu.append(empty);
                input.removeAttribute('aria-activedescendant');
            }
            menu.hidden = false;
            input.setAttribute('aria-expanded', 'true');
            status.textContent = matches.length ? `${matches.length} osób. Wybierz strzałkami i naciśnij Enter.` : 'Brak pasujących osób w Workspace.';
            select(0);
        }

        input.addEventListener('input', update, { signal });
        input.addEventListener('click', update, { signal });
        input.addEventListener('keydown', event => {
            if (menu.hidden || event.isComposing) return;
            if (event.key === 'Escape') {
                event.preventDefault(); event.stopPropagation(); close();
            } else if (matches.length && ['ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
                event.preventDefault(); event.stopPropagation();
                if (event.key === 'Enter') insert(matches[selected]);
                else select((selected + (event.key === 'ArrowDown' ? 1 : -1) + matches.length) % matches.length);
            } else if (['Tab', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) close();
        }, { signal });
        input.addEventListener('blur', close, { signal });
        input.form.addEventListener('submit', () => { syncMentions(); saveMentions(); }, { signal, capture: true });
        document.addEventListener('click', event => { if (!composer.contains(event.target)) close(); }, { signal });
    }
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
    else init();
    document.addEventListener('ancore:content-loaded', init);
})();
