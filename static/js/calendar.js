function initCalendarPage() {
    const configEl = document.getElementById('calendar-config');
    if (!configEl) {
        window.ancoreCalendarPageListenersController?.abort();
        window.ancoreCalendarPageListenersController = null;
        return;
    }

    if (configEl.dataset.calendarInitialized === 'true') return;
    configEl.dataset.calendarInitialized = 'true';

    if (window.ancoreCalendarPageListenersController) {
        window.ancoreCalendarPageListenersController.abort();
    }

    const pageListenersController = typeof AbortController === 'function' ? new AbortController() : null;
    window.ancoreCalendarPageListenersController = pageListenersController;
    const pageListenerOptions = pageListenersController ? { signal: pageListenersController.signal } : false;

    const config = JSON.parse(configEl.textContent);
    const csrfToken = config.csrfToken;
    const urls = config.urls;

    const MONTH_NAMES = [
        'styczeń', 'luty', 'marzec', 'kwiecień', 'maj', 'czerwiec',
        'lipiec', 'sierpień', 'wrzesień', 'październik', 'listopad', 'grudzień',
    ];
    const MONTH_NAMES_CAP = MONTH_NAMES.map((m) => m.charAt(0).toUpperCase() + m.slice(1));
    const DAY_NAMES = ['niedziela', 'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota'];
    const WEEKDAY_SHORT = ['Pon', 'Wto', 'Śro', 'Czw', 'Pią', 'Sob', 'Nie'];
    const MAX_EVENTS_PER_CELL = 3;
    const COLORS = ['red', 'blue', 'green', 'amber', 'slate'];

    let anchorDate = startOfDay(new Date(
        Number(config.initialYear) || new Date().getFullYear(),
        Math.max(0, (Number(config.initialMonth) || (new Date().getMonth() + 1)) - 1),
        Number(config.initialDay) || 1
    ));
    let currentView = 'month';
    let events = [];
    let selectedDate = cloneDate(anchorDate);
    let agendaMode = 'day';
    let searchQuery = '';
    let sourceFilter = '';
    const activeColors = new Set(COLORS);
    let saving = false;
    let dialogTrigger = null;
    let requestController = null;
    let loading = false;
    let loadFailed = false;
    let scrollTimeGrid = true;
    let fetchToken = 0;
    let pendingEventId = Number(config.initialEventId) || null;

    const periodLabel = document.getElementById('cal-period-label');
    const eventsSubtitle = document.getElementById('cal-events-subtitle');
    const eventsList = document.getElementById('calendar-events-list');
    const agenda = document.getElementById('calendar-agenda');
    const agendaToggle = document.getElementById('cal-toggle-agenda');
    const searchInput = document.getElementById('cal-search');
    const statusEl = document.getElementById('cal-status');
    const statusText = document.getElementById('cal-status-text');
    const retryButton = document.getElementById('cal-retry');
    const saveButton = document.getElementById('event-save-btn');
    const weekdaysHeader = document.getElementById('cal-weekdays-header');
    const viewContainers = {
        month: document.getElementById('calendar-view-month'),
        week: document.getElementById('calendar-view-week'),
        day: document.getElementById('calendar-view-day'),
        year: document.getElementById('calendar-view-year'),
    };
    const monthDaysEl = document.getElementById('calendar-days-month');
    const yearGridEl = document.getElementById('calendar-year-grid');
    const dialogOverlay = document.getElementById('event-dialog-overlay');
    const eventForm = document.getElementById('event-form');
    const eventIdInput = document.getElementById('event-id');
    const eventTitleInput = document.getElementById('event-title');
    const eventDescInput = document.getElementById('event-description');
    const eventAllDayInput = document.getElementById('event-all-day');
    const eventStartInput = document.getElementById('event-start');
    const eventEndInput = document.getElementById('event-end');
    const eventColorInput = document.getElementById('event-color');
    const eventDialogTitle = document.getElementById('event-dialog-title');
    const eventFormError = document.getElementById('event-form-error');
    const eventDeleteBtn = document.getElementById('event-delete-btn');
    const eventColorSelect = document.querySelector('[data-calendar-color-select]');
    const eventColorToggle = eventColorSelect?.querySelector('[data-calendar-color-toggle]');
    const eventColorMenu = eventColorSelect?.querySelector('[data-calendar-color-menu]');
    const eventColorLabel = eventColorSelect?.querySelector('[data-calendar-color-label]');
    const eventColorDot = eventColorSelect?.querySelector('[data-calendar-color-dot]');
    const eventColorOptions = Array.from(eventColorSelect?.querySelectorAll('[data-calendar-color-option]') || []);

    function apiUrl(key, id) {
        const pattern = urls[key];
        return id !== undefined && id !== null
            ? pattern.replace('__ID__', String(id))
            : pattern;
    }

    function pad(n) {
        return String(n).padStart(2, '0');
    }

    function cloneDate(d) {
        return new Date(d.getFullYear(), d.getMonth(), d.getDate());
    }

    function startOfDay(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
    }

    function endOfDay(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59, 999);
    }

    function toLocalISO(date) {
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
    }

    function toLocalInputValue(date) {
        return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
    }

    function parseLocalInput(value) {
        const [datePart, timePart] = value.split('T');
        const [y, m, d] = datePart.split('-').map(Number);
        const [hh, mm] = (timePart || '00:00').split(':').map(Number);
        return new Date(y, m - 1, d, hh, mm);
    }

    function isSameDay(a, b) {
        return a.getFullYear() === b.getFullYear()
            && a.getMonth() === b.getMonth()
            && a.getDate() === b.getDate();
    }

    function startOfWeek(date) {
        const d = cloneDate(date);
        let day = d.getDay() - 1;
        if (day < 0) day = 6;
        d.setDate(d.getDate() - day);
        return startOfDay(d);
    }

    function endOfWeek(date) {
        const end = cloneDate(startOfWeek(date));
        end.setDate(end.getDate() + 6);
        return endOfDay(end);
    }

    function addDays(date, days) {
        const d = cloneDate(date);
        d.setDate(d.getDate() + days);
        return d;
    }

    function getMonthGridBounds(year, monthIndex) {
        const firstDay = new Date(year, monthIndex, 1);
        let startOffset = firstDay.getDay() - 1;
        if (startOffset < 0) startOffset = 6;
        const gridStart = new Date(year, monthIndex, 1 - startOffset);
        const gridEnd = endOfWeek(new Date(year, monthIndex + 1, 0));
        return { gridStart, gridEnd };
    }

    function getFetchRange() {
        const y = anchorDate.getFullYear();
        const m = anchorDate.getMonth();

        switch (currentView) {
            case 'year':
                return {
                    start: new Date(y, 0, 1, 0, 0, 0, 0),
                    end: new Date(y, 11, 31, 23, 59, 59, 999),
                };
            case 'month': {
                const { gridStart, gridEnd } = getMonthGridBounds(y, m);
                return { start: startOfDay(gridStart), end: endOfDay(gridEnd) };
            }
            case 'week':
                return { start: startOfWeek(anchorDate), end: endOfWeek(anchorDate) };
            case 'day':
                return { start: startOfDay(anchorDate), end: endOfDay(anchorDate) };
            default:
                return { start: startOfDay(anchorDate), end: endOfDay(anchorDate) };
        }
    }

    function eventOccursOnDay(event, day) {
        const start = new Date(event.start);
        const end = new Date(event.end);
        return start <= endOfDay(day) && (end > startOfDay(day) || isSameDay(start, day));
    }

    function visibleEvents() {
        return events.filter((event) => (!sourceFilter || event.source === sourceFilter) && activeColors.has(event.color)
            && (!searchQuery || `${event.title} ${event.description || ''}`.toLocaleLowerCase('pl').includes(searchQuery)));
    }

    function eventsOnDay(day) {
        return visibleEvents().filter((event) => eventOccursOnDay(event, day))
            .sort((a, b) => Number(b.all_day) - Number(a.all_day) || new Date(a.start) - new Date(b.start));
    }

    function eventCountLabel(count) {
        if (count === 1) return '1 pozycja';
        return `${count} ${count % 10 >= 2 && count % 10 <= 4 && !(count % 100 >= 12 && count % 100 <= 14) ? 'pozycje' : 'pozycji'}`;
    }

    function dateLabel(date, weekday = false) {
        return new Intl.DateTimeFormat('pl-PL', { day: 'numeric', month: 'long', ...(weekday ? { weekday: 'long' } : {}) }).format(date);
    }

    function selectDay(day, focus = false) {
        selectedDate = cloneDate(day);
        agendaMode = 'day';
        agenda.classList.remove('u-hidden');
        agendaToggle.setAttribute('aria-expanded', 'true');
        renderCurrentView();
        if (focus) monthDaysEl.querySelector(`[data-date="${toLocalISO(day).slice(0, 10)}"]`)?.focus({ preventScroll: true });
    }

    function periodEvents() {
        if (currentView !== 'month') return visibleEvents();
        const start = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
        const end = new Date(anchorDate.getFullYear(), anchorDate.getMonth() + 1, 1);
        return visibleEvents().filter((event) => new Date(event.start) < end && new Date(event.end) >= start);
    }

    function formatEventTime(event) {
        if (event.all_day) return 'Cały dzień';
        const start = new Date(event.start);
        const end = new Date(event.end);
        if (isSameDay(start, end)) {
            return `${pad(start.getHours())}:${pad(start.getMinutes())}`;
        }
        return `${pad(start.getHours())}:${pad(start.getMinutes())} – ${pad(end.getHours())}:${pad(end.getMinutes())}`;
    }

    function formatShortDate(date) {
        return dateLabel(date);
    }

    function updatePeriodLabel() {
        const y = anchorDate.getFullYear();
        const m = anchorDate.getMonth();

        switch (currentView) {
            case 'year':
                periodLabel.textContent = String(y);
                break;
            case 'month':
                periodLabel.textContent = `${MONTH_NAMES_CAP[m]} ${y}`;
                break;
            case 'week': {
                const ws = startOfWeek(anchorDate);
                const we = endOfWeek(anchorDate);
                const labelYear = we.getFullYear();
                periodLabel.textContent = ws.getMonth() === we.getMonth()
                    ? `${ws.getDate()}–${dateLabel(we)} ${labelYear}`
                    : `${dateLabel(ws)} – ${dateLabel(we)} ${labelYear}`;
                break;
            }
            case 'day':
                periodLabel.textContent = `${dateLabel(anchorDate, true).replace(/^./, (letter) => letter.toUpperCase())} ${y}`;
                break;
            default:
                break;
        }
    }

    function updateEventsSubtitle() {
        const labels = { day: 'Dzień', week: 'Tydzień', month: 'Miesiąc', year: 'Rok' };
        eventsSubtitle.textContent = loading ? 'Wczytywanie…' : `${labels[currentView]} · ${eventCountLabel(periodEvents().length)}`;
    }

    function createEventButton(event, showTime) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `calendar-event calendar-event--${COLORS.includes(event.color) ? event.color : 'slate'}`;
        const eventStart = new Date(event.start), eventEnd = new Date(event.end);
        btn.title = `${event.title} · ${dateLabel(eventStart)} · ${event.all_day ? 'Cały dzień' : `${pad(eventStart.getHours())}:${pad(eventStart.getMinutes())} – ${!isSameDay(eventStart, eventEnd) ? dateLabel(eventEnd) + ' ' : ''}${pad(eventEnd.getHours())}:${pad(eventEnd.getMinutes())}`}`;
        if (event.url) btn.title = `${event.title} · Termin: ${dateLabel(eventStart)}, ${formatEventTime(event)} · Otwórz szczegóły`;
        if (showTime) {
            const time = document.createElement('span');
            time.className = 'calendar-event-time';
            time.textContent = event.all_day ? 'Cały dzień' : formatEventTime(event).split(' – ')[0];
            btn.appendChild(time);
        }
        const title = document.createElement('span');
        title.className = 'calendar-event-title';
        title.textContent = event.title;
        btn.appendChild(title);
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openDialog('edit', null, event);
        });
        return btn;
    }

    function appendEventsToCell(container, dayEvents, max, day) {
        const limit = max ?? MAX_EVENTS_PER_CELL;
        dayEvents.slice(0, limit).forEach((event) => container.appendChild(createEventButton(event, true)));
        if (dayEvents.length > limit) {
            const more = document.createElement('button');
            more.type = 'button';
            more.className = 'calendar-event-more';
            more.textContent = `+${dayEvents.length - limit} więcej`;
            more.addEventListener('click', (e) => {
                e.stopPropagation();
                selectDay(day);
                agenda.scrollIntoView({ block: 'nearest' });
                document.getElementById('cal-agenda-mode').focus({ preventScroll: true });
            });
            container.appendChild(more);
        }
    }

    function renderMonthView() {
        const today = startOfDay(new Date());
        const monthIndex = anchorDate.getMonth();
        const { gridStart, gridEnd } = getMonthGridBounds(anchorDate.getFullYear(), monthIndex);
        const focusedDate = monthDaysEl.contains(document.activeElement) ? document.activeElement.closest('.calendar-day')?.dataset.date : null;
        monthDaysEl.innerHTML = '';
        const days = [];
        for (let day = gridStart; day <= gridEnd; day = addDays(day, 1)) days.push(day);
        monthDaysEl.style.setProperty('--calendar-weeks', days.length / 7);
        let weekRow;
        days.forEach((dayDate, index) => {
            if (index % 7 === 0) {
                weekRow = document.createElement('div');
                weekRow.className = 'calendar-week-row';
                weekRow.setAttribute('role', 'row');
                monthDaysEl.appendChild(weekRow);
            }
            const cell = document.createElement('div');
            cell.className = 'calendar-day';
            cell.setAttribute('role', 'gridcell');
            cell.dataset.date = toLocalISO(dayDate).slice(0, 10);
            cell.tabIndex = isSameDay(dayDate, selectedDate) ? 0 : -1;
            cell.setAttribute('aria-selected', String(isSameDay(dayDate, selectedDate)));
            const dayEvents = eventsOnDay(dayDate);
            cell.setAttribute('aria-label', `${dateLabel(dayDate, true)}, ${eventCountLabel(dayEvents.length)}`);
            if (dayDate.getMonth() !== monthIndex) cell.classList.add('calendar-day--other');
            if ([0, 6].includes(dayDate.getDay())) cell.classList.add('calendar-day--weekend');
            if (isSameDay(dayDate, today)) cell.classList.add('calendar-day--today');
            if (isSameDay(dayDate, selectedDate)) cell.classList.add('calendar-day--selected');
            const head = document.createElement('div');
            head.className = 'calendar-day-head';
            const add = document.createElement('button');
            add.type = 'button';
            add.className = 'calendar-day-add';
            add.textContent = '+';
            add.setAttribute('aria-label', `Dodaj wydarzenie: ${dateLabel(dayDate)}`);
            add.addEventListener('click', (e) => {
                e.stopPropagation();
                selectedDate = cloneDate(dayDate);
                const preset = new Date(dayDate);
                preset.setHours(9);
                openDialog('create', preset, null);
            });
            const number = document.createElement('span');
            number.className = 'calendar-day-number';
            number.textContent = dayDate.getDate();
            if (isSameDay(dayDate, today)) number.setAttribute('aria-current', 'date');
            head.append(add, number);
            const wrap = document.createElement('div');
            wrap.className = 'calendar-day-events';
            const rowHeight = Math.max(110, monthDaysEl.clientHeight / (days.length / 7));
            const limit = Math.min(MAX_EVENTS_PER_CELL, Math.max(1, Math.floor((rowHeight - 57) / 29)));
            appendEventsToCell(wrap, dayEvents, limit, dayDate);
            cell.append(head, wrap);
            cell.addEventListener('click', () => selectDay(dayDate, true));
            cell.addEventListener('keydown', (e) => {
                if (e.target !== cell) return;
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectDay(dayDate, true); }
                const step = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }[e.key];
                if (step) {
                    e.preventDefault();
                    const next = addDays(dayDate, step);
                    if (next < gridStart || next > gridEnd) {
                        anchorDate = cloneDate(next);
                        fetchEvents();
                    }
                    selectDay(next, true);
                }
            });
            weekRow.appendChild(cell);
        });
        if (!monthDaysEl.querySelector('[tabindex="0"]')) monthDaysEl.querySelector('.calendar-day').tabIndex = 0;
        if (focusedDate) monthDaysEl.querySelector(`[data-date="${focusedDate}"]`)?.focus({ preventScroll: true });
    }

    function renderWeekView() {
        renderTimeView(viewContainers.week, startOfWeek(anchorDate), 7);
    }

    function renderDayView() {
        renderTimeView(viewContainers.day, anchorDate, 1);
    }

    function renderTimeView(container, firstDay, count) {
        const previousScroll = container.querySelector('.calendar-time-scroll')?.scrollTop;
        const previousHorizontalScroll = container.scrollLeft;
        container.innerHTML = '';
        const frame = document.createElement('div');
        frame.className = 'calendar-time-frame';
        frame.style.setProperty('--calendar-columns', count);
        const header = document.createElement('div');
        header.className = 'calendar-time-header';
        const zone = document.createElement('span');
        zone.className = 'calendar-time-zone';
        zone.textContent = 'Godz.';
        header.appendChild(zone);
        for (let i = 0; i < count; i++) {
            const day = addDays(firstDay, i);
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'calendar-week-day-head';
            button.textContent = `${DAY_NAMES[day.getDay()]} ${day.getDate()}`;
            if (isSameDay(day, new Date())) button.classList.add('calendar-week-day-head--today');
            button.addEventListener('click', () => { anchorDate = selectedDate = cloneDate(day); setView('day'); });
            header.appendChild(button);
        }
        const allDay = document.createElement('div');
        allDay.className = 'calendar-time-allday';
        const allDayLabel = document.createElement('span');
        allDayLabel.className = 'calendar-time-zone';
        allDayLabel.textContent = 'Cały dzień';
        allDay.appendChild(allDayLabel);
        for (let i = 0; i < count; i++) {
            const day = addDays(firstDay, i);
            const cell = document.createElement('div');
            cell.className = 'calendar-time-allday-cell';
            eventsOnDay(day).filter((event) => event.all_day).forEach((event) => cell.appendChild(createEventButton(event, false)));
            const add = document.createElement('button');
            add.type = 'button';
            add.className = 'calendar-allday-add';
            add.textContent = '+';
            add.setAttribute('aria-label', `Dodaj całodzienne wydarzenie: ${dateLabel(day)}`);
            add.addEventListener('click', () => { openDialog('create', day, null); eventAllDayInput.checked = true; applyAllDayTimes(); });
            cell.appendChild(add);
            allDay.appendChild(cell);
        }
        const scroll = document.createElement('div');
        scroll.className = 'calendar-time-scroll';
        const grid = document.createElement('div');
        grid.className = 'calendar-time-grid';
        const hours = document.createElement('div');
        hours.className = 'calendar-time-hours';
        for (let h = 0; h < 24; h++) {
            const label = document.createElement('span');
            label.textContent = `${pad(h)}:00`;
            hours.appendChild(label);
        }
        grid.appendChild(hours);
        for (let i = 0; i < count; i++) {
            const day = addDays(firstDay, i);
            const col = document.createElement('div');
            col.className = 'calendar-time-column';
            if (isSameDay(day, new Date())) col.classList.add('calendar-time-column--today');
            for (let h = 0; h < 24; h++) {
                const slot = document.createElement('button');
                slot.type = 'button';
                slot.className = 'calendar-time-slot';
                slot.setAttribute('aria-label', `Dodaj wydarzenie: ${dateLabel(day)}, ${pad(h)}:00`);
                slot.addEventListener('click', () => {
                    const preset = new Date(day);
                    preset.setHours(h);
                    openDialog('create', preset, null);
                });
                col.appendChild(slot);
            }
            const timed = eventsOnDay(day).filter((event) => !event.all_day).map((event) => {
                const start = new Date(event.start), end = new Date(event.end);
                const startMinute = start < startOfDay(day) ? 0 : start.getHours() * 60 + start.getMinutes();
                const endMinute = end > endOfDay(day) ? 1440 : end.getHours() * 60 + end.getMinutes();
                return { event, start: startMinute, end: Math.min(1440, Math.max(startMinute + 24, endMinute)) };
            }).sort((a, b) => a.start - b.start || b.end - a.end);
            // Connected overlap groups share the same lane count; adjacent events can reuse a lane.
            let group = [], groupEnd = -1;
            const drawGroup = () => {
                const lanes = [];
                group.forEach((item) => {
                    let lane = lanes.findIndex((end) => end <= item.start);
                    if (lane === -1) lane = lanes.length;
                    lanes[lane] = item.end;
                    item.lane = lane;
                });
                group.forEach((item) => {
                    const button = createEventButton(item.event, true);
                    button.classList.add('calendar-time-event');
                    button.style.top = `${item.start / 1440 * 100}%`;
                    button.style.height = `${(item.end - item.start) / 1440 * 100}%`;
                    button.style.left = `calc(${item.lane / lanes.length * 100}% + 3px)`;
                    button.style.width = `calc(${100 / lanes.length}% - 6px)`;
                    col.appendChild(button);
                });
            };
            timed.forEach((item) => {
                if (item.start >= groupEnd && group.length) { drawGroup(); group = []; }
                group.push(item);
                groupEnd = Math.max(group.length === 1 ? -1 : groupEnd, item.end);
            });
            drawGroup();
            if (isSameDay(day, new Date())) {
                const now = new Date();
                const line = document.createElement('div');
                line.className = 'calendar-now-line';
                line.style.top = `${(now.getHours() * 60 + now.getMinutes()) / 1440 * 100}%`;
                line.setAttribute('aria-label', `Teraz ${pad(now.getHours())}:${pad(now.getMinutes())}`);
                col.appendChild(line);
            }
            grid.appendChild(col);
        }
        scroll.appendChild(grid);
        frame.append(header, allDay, scroll);
        container.appendChild(frame);
        scroll.scrollTop = scrollTimeGrid ? 8 * 60 : previousScroll || 0;
        frame.style.setProperty('--calendar-scrollbar', `${scroll.offsetWidth - scroll.clientWidth}px`);
        container.scrollLeft = previousHorizontalScroll;
        scrollTimeGrid = false;
    }

    function renderYearView() {
        const year = anchorDate.getFullYear();
        const today = startOfDay(new Date());
        yearGridEl.innerHTML = '';

        for (let m = 0; m < 12; m += 1) {
            const mini = document.createElement('div');
            mini.className = 'calendar-year-month';

            const title = document.createElement('button');
            title.type = 'button';
            title.className = 'calendar-year-month-title';
            title.textContent = MONTH_NAMES_CAP[m];
            title.addEventListener('click', () => {
                anchorDate = selectedDate = new Date(year, m, 1);
                setView('month');
            });
            mini.appendChild(title);

            const weekdays = document.createElement('div');
            weekdays.className = 'calendar-year-weekdays';
            weekdays.innerHTML = '<span>P</span><span>W</span><span>Ś</span><span>C</span><span>P</span><span class="calendar-weekend">S</span><span class="calendar-weekend">N</span>';
            mini.appendChild(weekdays);

            const daysGrid = document.createElement('div');
            daysGrid.className = 'calendar-year-days';

            const { gridStart } = getMonthGridBounds(year, m);

            for (let i = 0; i < 42; i += 1) {
                const dayDate = addDays(gridStart, i);
                const inMonth = dayDate.getMonth() === m;

                const cell = document.createElement('button');
                cell.type = 'button';
                cell.className = 'calendar-year-day';
                if (!inMonth) {
                    cell.classList.add('calendar-year-day--other');
                    cell.disabled = true;
                } else {
                    cell.textContent = String(dayDate.getDate());
                    if (isSameDay(dayDate, today)) cell.classList.add('calendar-year-day--today');
                    const count = eventsOnDay(dayDate).length;
                    if (count > 0) {
                        cell.classList.add('calendar-year-day--has-events');
                        cell.title = `${count} wydarzeń`;
                    }
                    cell.addEventListener('click', () => {
                        anchorDate = selectedDate = cloneDate(dayDate);
                        setView('day');
                    });
                }
                daysGrid.appendChild(cell);
            }
            mini.appendChild(daysGrid);
            yearGridEl.appendChild(mini);
        }
    }

    function renderEventsList() {
        eventsList.innerHTML = '';
        document.getElementById('cal-agenda-title').textContent = agendaMode === 'day' ? 'Plan dnia' : 'Wydarzenia';
        document.getElementById('cal-agenda-mode').textContent = agendaMode === 'day' ? 'Cały okres' : 'Plan dnia';
        document.getElementById('cal-agenda-date').textContent = agendaMode === 'day' ? dateLabel(selectedDate, true) : periodLabel.textContent;
        const sorted = (agendaMode === 'day' ? eventsOnDay(selectedDate) : periodEvents()).sort((a, b) => new Date(a.start) - new Date(b.start));
        document.getElementById('cal-agenda-count').textContent = loading ? 'Wczytywanie…' : eventCountLabel(sorted.length);
        if (!sorted.length) {
            const empty = document.createElement('li');
            empty.className = 'calendar-events-empty';
            const title = document.createElement('strong');
            title.textContent = loading ? 'Wczytywanie pozycji…' : loadFailed ? 'Nie udało się wczytać pozycji' : searchQuery || sourceFilter || activeColors.size < COLORS.length ? 'Brak pasujących pozycji' : 'Czas na Twoje plany';
            const description = document.createElement('span');
            description.textContent = loading ? 'Za chwilę pojawi się Twój plan.' : loadFailed ? 'Spróbuj ponownie za pomocą przycisku nad kalendarzem.' : searchQuery || sourceFilter || activeColors.size < COLORS.length ? 'Zmień wyszukiwanie, rodzaj pozycji lub kolory.' : 'Dodaj wydarzenie i zaplanuj ten dzień.';
            empty.append(title, description);
            eventsList.appendChild(empty);
            return;
        }
        let lastDate = '';
        sorted.forEach((event) => {
            const start = new Date(event.start), end = new Date(event.end);
            if (agendaMode === 'period' && dateLabel(start) !== lastDate) {
                lastDate = dateLabel(start);
                const heading = document.createElement('li');
                heading.className = 'calendar-agenda-group';
                heading.textContent = dateLabel(start, true);
                eventsList.appendChild(heading);
            }
            const li = document.createElement('li');
            const button = document.createElement('button');
            button.type = 'button';
            button.className = `calendar-list-item calendar-list-item--${COLORS.includes(event.color) ? event.color : 'slate'}`;
            const time = document.createElement('span');
            time.className = 'calendar-list-time';
            time.textContent = event.all_day ? 'Cały dzień' : `${pad(start.getHours())}:${pad(start.getMinutes())}`;
            const body = document.createElement('span');
            body.className = 'calendar-list-body';
            const title = document.createElement('span');
            title.className = 'calendar-list-title';
            title.textContent = event.title;
            const detail = document.createElement('span');
            detail.className = 'calendar-list-date';
            detail.textContent = !isSameDay(start, end) ? `${dateLabel(start)} – ${dateLabel(end)}` : event.all_day ? 'Cały dzień' : `${pad(start.getHours())}:${pad(start.getMinutes())} – ${pad(end.getHours())}:${pad(end.getMinutes())} · ${Math.round((end - start) / 60000)} min`;
            if (event.url) detail.textContent = `Termin · ${formatEventTime(event)} · Otwórz szczegóły`;
            body.append(title, detail);
            button.append(time, body);
            button.addEventListener('click', () => openDialog('edit', null, event));
            li.appendChild(button);
            eventsList.appendChild(li);
        });
    }

    function setActiveViewContainer() {
        weekdaysHeader.classList.toggle('u-hidden', currentView !== 'month');
        Object.entries(viewContainers).forEach(([view, el]) => {
            if (!el) return;
            const active = view === currentView;
            el.classList.toggle('u-hidden', !active);
            el.classList.toggle('is-active', active);
        });
    }

    function renderCurrentView() {
        updatePeriodLabel();
        updateEventsSubtitle();
        setActiveViewContainer();

        switch (currentView) {
            case 'month': renderMonthView(); break;
            case 'week': renderWeekView(); break;
            case 'day': renderDayView(); break;
            case 'year': renderYearView(); break;
            default: break;
        }
        renderEventsList();
    }

    function setView(view) {
        if (!view || view === currentView) {
            renderCurrentView();
            return;
        }
        if (!viewContainers[view]) return;
        currentView = view;
        anchorDate = cloneDate(selectedDate);
        scrollTimeGrid = true;

        document.querySelectorAll('.calendar-view-btn').forEach((btn) => {
            const active = btn.dataset.view === view;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        document.querySelectorAll('.calendar-mini-nav__button').forEach((btn) => {
            const active = btn.dataset.view === view;
            btn.classList.toggle('is-active', active);
            btn.setAttribute('aria-pressed', active ? 'true' : 'false');
        });

        renderCurrentView();
        fetchEvents();
    }

    async function fetchEvents() {
        const token = ++fetchToken;
        requestController?.abort();
        requestController = new AbortController();
        const { start, end } = getFetchRange();
        const params = new URLSearchParams({ start: start.toISOString(), end: end.toISOString() });
        loading = true;
        loadFailed = false;
        events = [];
        statusEl.classList.remove('u-hidden');
        statusText.textContent = 'Wczytywanie pozycji…';
        retryButton.classList.add('u-hidden');
        document.querySelector('.calendar-main').setAttribute('aria-busy', 'true');
        renderCurrentView();
        try {
            const response = await fetch(`${urls.events}?${params}`, { signal: requestController.signal });
            const data = await response.json();
            if (token !== fetchToken || pageListenersController?.signal.aborted) return;
            if (!response.ok || data.status !== 'success') throw new Error('events');
            events = data.events;
            statusEl.classList.add('u-hidden');
        } catch (error) {
            if (error.name === 'AbortError' || token !== fetchToken) return;
            loadFailed = true;
            statusText.textContent = 'Nie udało się wczytać pozycji. Sprawdź połączenie i spróbuj ponownie.';
            retryButton.classList.remove('u-hidden');
        } finally {
            if (token === fetchToken && !pageListenersController?.signal.aborted) {
                loading = false;
                document.querySelector('.calendar-main').setAttribute('aria-busy', 'false');
                renderCurrentView();
                if (pendingEventId && !loadFailed) {
                    const requestedEvent = events.find((event) => Number(event.id) === pendingEventId);
                    pendingEventId = null;
                    if (requestedEvent) openDialog('edit', null, requestedEvent);
                }
            }
        }
    }

    function navigate(delta) {
        const y = anchorDate.getFullYear();
        const m = anchorDate.getMonth();
        const d = anchorDate.getDate();

        switch (currentView) {
            case 'year':
                anchorDate = new Date(y + delta, m, Math.min(d, new Date(y + delta, m + 1, 0).getDate()));
                break;
            case 'month':
                anchorDate = new Date(y, m + delta, Math.min(d, new Date(y, m + delta + 1, 0).getDate()));
                break;
            case 'week':
                anchorDate = addDays(anchorDate, delta * 7);
                break;
            case 'day':
                anchorDate = addDays(anchorDate, delta);
                break;
            default:
                break;
        }

        selectedDate = cloneDate(anchorDate);
        renderCurrentView();
        fetchEvents();
    }

    function goToToday() {
        anchorDate = selectedDate = startOfDay(new Date());
        renderCurrentView();
        fetchEvents();
    }

    function showFormError(message) {
        eventFormError.textContent = message;
        eventFormError.classList.remove('u-hidden');
    }

    function clearFormError() {
        eventFormError.textContent = '';
        eventFormError.classList.add('u-hidden');
    }

    function selectedEventColorOption() {
        return eventColorOptions.find((option) => option.classList.contains('is-selected'))
            || eventColorOptions[0];
    }

    function syncEventColorSelect(value = eventColorInput?.value || 'red', dispatchChange = false) {
        if (!eventColorInput || !eventColorOptions.length) return;

        const option = eventColorOptions.find((item) => item.dataset.value === value) || eventColorOptions[0];
        const nextValue = option.dataset.value || '';
        eventColorInput.value = nextValue;

        if (eventColorLabel) {
            eventColorLabel.textContent = option.dataset.label || option.textContent.trim();
        }

        if (eventColorDot) {
            eventColorDot.className = `calendar-color-dot calendar-color-dot--${nextValue}`;
        }

        eventColorOptions.forEach((item) => {
            const isSelected = item === option;
            item.classList.toggle('is-selected', isSelected);
            item.setAttribute('aria-selected', String(isSelected));
            item.tabIndex = isSelected ? 0 : -1;
        });

        if (dispatchChange) {
            eventColorInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    function closeEventColorSelect(restoreFocus = false) {
        if (!eventColorSelect) return;

        window.AncoreDropdownLayer?.hide(eventColorMenu);
        eventColorSelect.classList.remove('is-open');
        eventColorToggle?.setAttribute('aria-expanded', 'false');
        if (eventColorMenu) eventColorMenu.hidden = true;
        if (restoreFocus) eventColorToggle?.focus({ preventScroll: true });
    }

    function openEventColorSelect(focusSelected = false) {
        if (!eventColorSelect) return;

        syncEventColorSelect();
        eventColorSelect.classList.add('is-open');
        eventColorToggle?.setAttribute('aria-expanded', 'true');
        if (eventColorMenu) eventColorMenu.hidden = false;
        window.AncoreDropdownLayer?.open(eventColorMenu, eventColorToggle, () => closeEventColorSelect());

        if (focusSelected) {
            selectedEventColorOption()?.focus({ preventScroll: true });
        }
    }

    function selectEventColorOption(option) {
        if (!option || option.disabled) return;

        syncEventColorSelect(option.dataset.value || '', true);
        closeEventColorSelect(true);
    }

    function focusEventColorOption(direction) {
        if (!eventColorOptions.length) return;

        if (!eventColorSelect?.classList.contains('is-open')) {
            openEventColorSelect();
        }

        const focusedIndex = eventColorOptions.indexOf(document.activeElement);
        const selectedIndex = eventColorOptions.indexOf(selectedEventColorOption());
        const currentIndex = focusedIndex >= 0 ? focusedIndex : Math.max(0, selectedIndex);
        const nextIndex = (currentIndex + direction + eventColorOptions.length) % eventColorOptions.length;
        eventColorOptions[nextIndex]?.focus({ preventScroll: true });
    }

    function handleEventColorKeydown(e) {
        if (!eventColorSelect?.contains(e.target)) return false;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            focusEventColorOption(1);
            return true;
        }

        if (e.key === 'ArrowUp') {
            e.preventDefault();
            focusEventColorOption(-1);
            return true;
        }

        if (e.key === 'Home') {
            e.preventDefault();
            openEventColorSelect();
            eventColorOptions[0]?.focus({ preventScroll: true });
            return true;
        }

        if (e.key === 'End') {
            e.preventDefault();
            openEventColorSelect();
            eventColorOptions[eventColorOptions.length - 1]?.focus({ preventScroll: true });
            return true;
        }

        if (e.key === 'Escape' && eventColorSelect.classList.contains('is-open')) {
            e.preventDefault();
            closeEventColorSelect(true);
            return true;
        }

        if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('[data-calendar-color-option]')) {
            e.preventDefault();
            selectEventColorOption(e.target);
            return true;
        }

        return false;
    }

    function openDialog(mode, presetDate, event) {
        if (event?.url) {
            window.location.assign(event.url);
            return;
        }
        if (saving) return;
        dialogTrigger = document.activeElement;
        closeEventColorSelect();
        clearFormError();
        eventForm.reset();

        if (mode === 'create') {
            eventDialogTitle.textContent = 'Nowe wydarzenie';
            eventDeleteBtn.classList.add('u-hidden');
            eventIdInput.value = '';

            const base = presetDate ? startOfDay(presetDate) : startOfDay(selectedDate);
            const start = new Date(base);
            start.setHours(presetDate?.getHours?.() ?? 9, presetDate?.getMinutes?.() ?? 0, 0, 0);
            const end = new Date(start);
            end.setHours(start.getHours() + 1);
            eventStartInput.value = toLocalInputValue(start);
            eventEndInput.value = toLocalInputValue(end);
            eventColorInput.value = 'red';
        } else {
            eventDialogTitle.textContent = 'Edytuj wydarzenie';
            eventDeleteBtn.classList.remove('u-hidden');
            eventIdInput.value = event.id;
            eventTitleInput.value = event.title;
            eventDescInput.value = event.description || '';
            eventAllDayInput.checked = event.all_day;
            eventStartInput.value = toLocalInputValue(new Date(event.start));
            eventEndInput.value = toLocalInputValue(new Date(event.end));
            eventColorInput.value = event.color;
        }

        syncEventColorSelect(eventColorInput.value);
        dialogOverlay.classList.add('active');
        dialogOverlay.setAttribute('aria-hidden', 'false');
        eventTitleInput.focus();
    }

    function closeDialog() {
        if (saving) return;
        closeEventColorSelect();
        dialogOverlay.classList.remove('active');
        dialogOverlay.setAttribute('aria-hidden', 'true');
        clearFormError();
        if (dialogTrigger?.isConnected) dialogTrigger.focus({ preventScroll: true });
        else document.getElementById('cal-today')?.focus();
    }

    function applyAllDayTimes() {
        if (!eventAllDayInput.checked || !eventStartInput.value || !eventEndInput.value) return;
        const start = parseLocalInput(eventStartInput.value);
        const end = parseLocalInput(eventEndInput.value);
        start.setHours(0, 0, 0, 0);
        end.setHours(23, 59, 0, 0);
        eventStartInput.value = toLocalInputValue(start);
        eventEndInput.value = toLocalInputValue(end);
    }

    function setSaving(value) {
        saving = value;
        saveButton.disabled = value;
        eventDeleteBtn.disabled = value;
        saveButton.textContent = value ? 'Zapisywanie…' : 'Zapisz';
        eventForm.setAttribute('aria-busy', String(value));
    }

    async function saveEvent(e) {
        e.preventDefault();
        if (saving) return;
        clearFormError();
        if (!eventTitleInput.value.trim()) { showFormError('Wpisz tytuł wydarzenia.'); eventTitleInput.focus(); return; }
        if (!eventStartInput.value || !eventEndInput.value) { showFormError('Uzupełnij datę rozpoczęcia i zakończenia.'); return; }
        applyAllDayTimes();
        if (parseLocalInput(eventEndInput.value) < parseLocalInput(eventStartInput.value)) {
            showFormError('Zakończenie nie może być wcześniejsze niż rozpoczęcie.'); eventEndInput.focus(); return;
        }
        const formData = new FormData(eventForm);
        formData.set('title', eventTitleInput.value.trim());
        formData.set('description', eventDescInput.value.trim());
        formData.set('all_day', eventAllDayInput.checked ? 'on' : '');
        const eventId = eventIdInput.value;
        setSaving(true);
        try {
            const response = await fetch(eventId ? apiUrl('update', eventId) : urls.create, {
                method: 'POST', headers: { 'X-CSRFToken': csrfToken }, body: formData,
            });
            const data = await response.json();
            if (!response.ok || data.status !== 'success') {
                showFormError(data.errors ? Object.values(data.errors).flat()[0] || 'Sprawdź dane wydarzenia.' : data.message || 'Nie udało się zapisać wydarzenia.');
                return;
            }
            agendaMode = 'day';
            selectedDate = startOfDay(new Date(data.event.start));
            anchorDate = cloneDate(selectedDate);
            setSaving(false);
            closeDialog();
            await fetchEvents();
        } catch (error) {
            showFormError('Nie udało się zapisać wydarzenia. Sprawdź połączenie i spróbuj ponownie.');
        } finally { setSaving(false); }
    }

    async function deleteEvent() {
        const eventId = eventIdInput.value;
        if (!eventId || saving) return;
        showConfirmModal({
            title: 'Usuń wydarzenie', message: 'Czy na pewno chcesz usunąć to wydarzenie?',
            confirmText: 'Usuń', confirmClass: 'btn-danger',
            onConfirm: async () => {
                setSaving(true);
                try {
                    const response = await fetch(apiUrl('delete', eventId), { method: 'POST', headers: { 'X-CSRFToken': csrfToken } });
                    const data = await response.json();
                    if (!response.ok || data.status !== 'success') throw new Error('delete');
                    setSaving(false);
                    closeDialog();
                    await fetchEvents();
                } catch (error) { showFormError('Nie udało się usunąć wydarzenia. Spróbuj ponownie.'); }
                finally { setSaving(false); }
            },
        });
    }

    document.getElementById('cal-prev')?.addEventListener('click', () => navigate(-1), pageListenerOptions);
    document.getElementById('cal-next')?.addEventListener('click', () => navigate(1), pageListenerOptions);
    document.getElementById('cal-today')?.addEventListener('click', goToToday, pageListenerOptions);
    document.getElementById('cal-add-event')?.addEventListener('click', () => openDialog('create', null, null), pageListenerOptions);
    document.querySelectorAll('[data-calendar-add]').forEach((btn) => {
        btn.addEventListener('click', () => openDialog('create', null, null), pageListenerOptions);
    });

    document.querySelectorAll('.calendar-view-btn').forEach((btn) => {
        btn.addEventListener('click', () => setView(btn.dataset.view), pageListenerOptions);
    });
    document.querySelectorAll('.calendar-mini-nav__button').forEach((btn) => {
        btn.addEventListener('click', () => setView(btn.dataset.view), pageListenerOptions);
    });

    document.querySelectorAll('.cancel-event-btn').forEach((btn) => {
        btn.addEventListener('click', closeDialog, pageListenerOptions);
    });
    eventDeleteBtn?.addEventListener('click', deleteEvent, pageListenerOptions);
    eventForm?.addEventListener('submit', saveEvent, pageListenerOptions);
    eventAllDayInput?.addEventListener('change', applyAllDayTimes, pageListenerOptions);
    eventColorToggle?.addEventListener('click', () => {
        if (eventColorSelect?.classList.contains('is-open')) {
            closeEventColorSelect();
        } else {
            openEventColorSelect();
        }
    }, pageListenerOptions);
    eventColorOptions.forEach((option) => {
        option.addEventListener('click', () => selectEventColorOption(option), pageListenerOptions);
    });
    eventColorInput?.addEventListener('change', () => syncEventColorSelect(eventColorInput.value), pageListenerOptions);

    dialogOverlay?.addEventListener('click', (e) => {
        if (e.target === dialogOverlay) closeDialog();
    }, pageListenerOptions);

    document.addEventListener('click', (e) => {
        if (!eventColorSelect?.contains(e.target)) closeEventColorSelect();
    }, pageListenerOptions);

    document.addEventListener('keydown', (e) => {
        if (handleEventColorKeydown(e)) return;
        if (e.key === 'Escape') {
            const colorMenu = document.querySelector('.calendar-color-filter[open]');
            if (colorMenu) {
                colorMenu.open = false;
                colorMenu.querySelector('summary').focus();
                return;
            }
        }

        if (dialogOverlay?.classList.contains('active')) {
            if (document.querySelector('.confirm-modal-overlay.is-visible')) return;
            if (e.key === 'Escape') { e.preventDefault(); closeDialog(); }
            if (e.key === 'Tab') {
                const controls = [...dialogOverlay.querySelectorAll('button, input, textarea, select, [tabindex="0"]')]
                    .filter((el) => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length);
                const first = controls[0], last = controls[controls.length - 1];
                if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
                else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
            }
        }
    }, pageListenerOptions);

    searchInput.addEventListener('input', () => {
        searchQuery = searchInput.value.trim().toLocaleLowerCase('pl');
        if (searchQuery) agendaMode = 'period';
        renderCurrentView();
    }, pageListenerOptions);
    document.getElementById('cal-source-filter').addEventListener('change', (event) => {
        sourceFilter = event.target.value;
        renderCurrentView();
    }, pageListenerOptions);
    document.querySelectorAll('[data-color-filter]').forEach((button) => {
        button.addEventListener('click', () => {
            const color = button.dataset.colorFilter;
            if (activeColors.has(color)) activeColors.delete(color); else activeColors.add(color);
            document.querySelectorAll(`[data-color-filter="${color}"]`).forEach((filter) => filter.setAttribute('aria-pressed', String(activeColors.has(color))));
            renderCurrentView();
        }, pageListenerOptions);
    });
    agendaToggle.addEventListener('click', () => {
        const hidden = agenda.classList.toggle('u-hidden');
        agendaToggle.setAttribute('aria-expanded', String(!hidden));
    }, pageListenerOptions);
    document.getElementById('cal-agenda-mode').addEventListener('click', () => {
        agendaMode = agendaMode === 'day' ? 'period' : 'day';
        renderEventsList();
    }, pageListenerOptions);
    retryButton.addEventListener('click', fetchEvents, pageListenerOptions);
    document.addEventListener('click', (event) => {
        document.querySelectorAll('.calendar-color-filter[open]').forEach((menu) => {
            if (!menu.contains(event.target)) menu.open = false;
        });
    }, pageListenerOptions);
    const resizeObserver = new ResizeObserver(() => { if (currentView === 'month') renderMonthView(); });
    resizeObserver.observe(monthDaysEl);
    pageListenersController?.signal.addEventListener('abort', () => resizeObserver.disconnect());
    let displayedToday = toLocalISO(new Date()).slice(0, 10);
    const clockTimer = setInterval(() => {
        const now = new Date();
        const today = toLocalISO(now).slice(0, 10);
        if (today !== displayedToday) {
            displayedToday = today;
            renderCurrentView();
        }
        document.querySelectorAll('.calendar-now-line').forEach((line) => {
            line.style.top = `${(now.getHours() * 60 + now.getMinutes()) / 1440 * 100}%`;
            line.setAttribute('aria-label', `Teraz ${pad(now.getHours())}:${pad(now.getMinutes())}`);
        });
    }, 60000);
    pageListenersController?.signal.addEventListener('abort', () => clearInterval(clockTimer));
    pageListenersController?.signal.addEventListener('abort', () => requestController?.abort());
    syncEventColorSelect();
    renderCurrentView();
    fetchEvents();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCalendarPage);
} else {
    initCalendarPage();
}

document.addEventListener('ancore:content-loaded', initCalendarPage);
