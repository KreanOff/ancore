function initCalendarPage() {
    if (document.querySelector('[data-react-root="page"]')) {
        window.ancoreCalendarPageListenersController?.abort();
        return;
    }
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
    const DEFAULT_EVENT_COLOR = '#e04f63';
    const EVENT_COLORS = {
        red: [DEFAULT_EVENT_COLOR, '#fff1f3'],
        blue: ['#4f7edb', '#edf3ff'],
        green: ['#43a36a', '#edf9f1'],
        amber: ['#d79a35', '#fff7e8'],
        slate: ['#7b8493', '#f1f3f6'],
    };

    let anchorDate = startOfDay(new Date(
        Number(config.initialYear) || new Date().getFullYear(),
        Math.max(0, (Number(config.initialMonth) || (new Date().getMonth() + 1)) - 1),
        Number(config.initialDay) || 1
    ));
    let currentView = 'month';
    let events = [];
    let selectedDate = cloneDate(anchorDate);
    let searchQuery = '';
    let saving = false;
    let editedEvent = null;
    let dialogTrigger = null;
    let requestController = null;
    let loading = false;
    let loadFailed = false;
    let scrollTimeGrid = true;
    let fetchToken = 0;
    let pendingEventId = Number(config.initialEventId) || null;

    const periodLabel = document.getElementById('cal-period-label');
    const eventsSubtitle = document.getElementById('cal-events-subtitle');
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
    const eventColorPicker = document.querySelector('[data-calendar-color-picker]');
    const eventColorReset = document.querySelector('[data-calendar-color-reset]');
    const eventColorPreview = document.querySelector('[data-calendar-color-preview]');
    const eventColorError = document.getElementById('event-color-error');

    function calendarColor(value) {
        const color = String(value || '').trim().toLowerCase();
        if (/^#[0-9a-f]{6}$/.test(color)) return color;
        return Object.hasOwn(EVENT_COLORS, color) ? EVENT_COLORS[color][0] : DEFAULT_EVENT_COLOR;
    }

    function calendarColorClass(value) {
        return Object.hasOwn(EVENT_COLORS, value) ? value : 'custom';
    }

    function applyEventColor(element, value) {
        const color = calendarColor(value);
        const background = Object.values(EVENT_COLORS).find(([hex]) => hex === color)?.[1];
        element.style.setProperty('--calendar-event-color', color);
        element.style.setProperty('--calendar-event-bg', background || `color-mix(in srgb, ${color} 10%, #ffffff)`);
        element.style.setProperty('--calendar-event-ink', 'var(--text-primary)');
    }

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

    function eventDate(event, name = 'start') {
        return new Date(event.all_day ? event[name].slice(0, 19) : event[name]);
    }

    function eventInputValue(event, name) {
        return event.all_day ? event[name].slice(0, 16) : toLocalInputValue(eventDate(event, name));
    }

    function eventDateValue(value, allDay, original, name) {
        if (allDay) return value;
        if (original && !original.all_day && eventInputValue(original, name) === value) return original[name];
        const date = new Date(value);
        const repeated = [-1, 1].some((direction) => {
            const offset = new Date(date.getTime() + direction * 86400000).getTimezoneOffset();
            return offset !== date.getTimezoneOffset()
                && toLocalInputValue(new Date(date.getTime() + (offset - date.getTimezoneOffset()) * 60000)) === value.slice(0, 16);
        });
        if (Number.isNaN(date.getTime()) || toLocalInputValue(date) !== value.slice(0, 16) || repeated) {
            throw new Error('Wybierz prawidłową datę i godzinę. Ta godzina nie istnieje lub występuje dwukrotnie po zmianie czasu.');
        }
        return date.toISOString();
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
        const start = eventDate(event);
        const end = eventDate(event, 'end');
        return start <= endOfDay(day) && (end > startOfDay(day) || isSameDay(start, day));
    }

    function visibleEvents() {
        return events.filter((event) => !searchQuery
            || `${event.title} ${event.description || ''}`.toLocaleLowerCase('pl').includes(searchQuery));
    }

    function eventsOnDay(day) {
        return visibleEvents().filter((event) => eventOccursOnDay(event, day))
            .sort((a, b) => Number(b.all_day) - Number(a.all_day) || eventDate(a) - eventDate(b));
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
        renderCurrentView();
        if (focus) monthDaysEl.querySelector(`[data-date="${toLocalISO(day).slice(0, 10)}"]`)?.focus({ preventScroll: true });
    }

    function periodEvents() {
        if (currentView !== 'month') return visibleEvents();
        const start = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
        const end = new Date(anchorDate.getFullYear(), anchorDate.getMonth() + 1, 1);
        return visibleEvents().filter((event) => eventDate(event) < end && eventDate(event, 'end') >= start);
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
        btn.className = `calendar-event calendar-event--${calendarColorClass(event.color)}`;
        applyEventColor(btn, event.color);
        const eventStart = eventDate(event), eventEnd = eventDate(event, 'end');
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
                selectedDate = cloneDate(day);
                setView('day');
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
        document.querySelectorAll('.calendar-mini-nav__button, [data-calendar-view-tab]').forEach((btn) => {
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
        eventColorInput?.removeAttribute('aria-invalid');
        eventColorPicker?.removeAttribute('aria-invalid');
        if (eventColorError) {
            eventColorError.textContent = '';
            eventColorError.classList.add('u-hidden');
        }
    }

    function syncEventColor() {
        if (!eventColorInput) return;
        const color = calendarColor(eventColorInput.value);
        if (eventColorPicker) eventColorPicker.value = color;
        if (eventColorPreview) applyEventColor(eventColorPreview, color);
    }

    function chooseEventColor(value) {
        if (!eventColorInput || saving) return;
        eventColorInput.value = value;
        eventColorInput.dispatchEvent(new Event('input', { bubbles: true }));
        eventColorInput.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function openDialog(mode, presetDate, event) {
        if (event?.url) {
            if (window.AncoreApp?.canNavigatePartially(event.url)) window.AncoreApp.navigate(event.url);
            else window.location.assign(event.url);
            return;
        }
        if (saving) return;
        dialogTrigger = document.activeElement;
        clearFormError();
        eventForm.reset();
        editedEvent = mode === 'create' ? null : event;

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
            eventColorInput.value = DEFAULT_EVENT_COLOR;
        } else {
            eventDialogTitle.textContent = 'Edytuj wydarzenie';
            eventDeleteBtn.classList.remove('u-hidden');
            eventIdInput.value = event.id;
            eventTitleInput.value = event.title;
            eventDescInput.value = event.description || '';
            eventAllDayInput.checked = event.all_day;
            eventStartInput.value = eventInputValue(event, 'start');
            eventEndInput.value = eventInputValue(event, 'end');
            eventColorInput.value = calendarColor(event.color);
        }

        syncEventColor();
        dialogOverlay.classList.add('active');
        dialogOverlay.setAttribute('aria-hidden', 'false');
        eventTitleInput.focus();
    }

    function closeDialog() {
        if (saving) return;
        dialogOverlay.classList.remove('active');
        dialogOverlay.setAttribute('aria-hidden', 'true');
        clearFormError();
        if (dialogTrigger?.isConnected) dialogTrigger.focus({ preventScroll: true });
        else document.getElementById('cal-today')?.focus();
    }

    function applyAllDayTimes() {
        if (!eventAllDayInput.checked || !eventStartInput.value || !eventEndInput.value) return;
        eventStartInput.value = eventStartInput.value.slice(0, 10) + 'T00:00';
        eventEndInput.value = eventEndInput.value.slice(0, 10) + 'T23:59';
    }

    function setSaving(value) {
        saving = value;
        saveButton.disabled = value;
        eventDeleteBtn.disabled = value;
        saveButton.textContent = value ? 'Zapisywanie…' : 'Zapisz';
        eventForm.setAttribute('aria-busy', String(value));
        for (const control of [eventColorInput, eventColorPicker, eventColorReset]) {
            if (control) control.disabled = value;
        }
    }

    async function saveEvent(e) {
        e.preventDefault();
        if (saving) return;
        clearFormError();
        if (!eventTitleInput.value.trim()) { showFormError('Wpisz tytuł wydarzenia.'); eventTitleInput.focus(); return; }
        if (!eventStartInput.value || !eventEndInput.value) { showFormError('Uzupełnij datę rozpoczęcia i zakończenia.'); return; }
        applyAllDayTimes();
        const formData = new FormData(eventForm);
        formData.set('title', eventTitleInput.value.trim());
        formData.set('description', eventDescInput.value.trim());
        formData.set('all_day', eventAllDayInput.checked ? 'on' : '');
        try {
            for (const name of ['start', 'end']) {
                formData.set(name, eventDateValue(formData.get(name), eventAllDayInput.checked, editedEvent, name));
            }
        } catch (error) {
            showFormError(error.message);
            return;
        }
        if (new Date(formData.get('end')) < new Date(formData.get('start'))) {
            showFormError('Zakończenie nie może być wcześniejsze niż rozpoczęcie.'); eventEndInput.focus(); return;
        }
        const eventId = eventIdInput.value;
        setSaving(true);
        try {
            const response = await fetch(eventId ? apiUrl('update', eventId) : urls.create, {
                method: 'POST', headers: { 'X-CSRFToken': csrfToken }, body: formData,
            });
            const data = await response.json();
            if (!response.ok || data.status !== 'success') {
                showFormError(data.errors ? Object.values(data.errors).flat()[0] || 'Sprawdź dane wydarzenia.' : data.message || 'Nie udało się zapisać wydarzenia.');
                if (data.errors?.color?.length && eventColorError) {
                    eventColorError.textContent = data.errors.color.join(' ');
                    eventColorError.classList.remove('u-hidden');
                    eventColorInput?.setAttribute('aria-invalid', 'true');
                    eventColorPicker?.setAttribute('aria-invalid', 'true');
                    setSaving(false);
                    eventColorInput?.focus();
                }
                return;
            }
            selectedDate = startOfDay(eventDate(data.event));
            anchorDate = cloneDate(selectedDate);
            setSaving(false);
            closeDialog();
            window.dispatchEvent(new Event('ancore:calendar-changed'));
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
                    window.dispatchEvent(new Event('ancore:calendar-changed'));
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
    document.querySelectorAll('.calendar-mini-nav__button, [data-calendar-view-tab]').forEach((btn) => {
        btn.addEventListener('click', () => setView(btn.dataset.view), pageListenerOptions);
    });

    document.querySelectorAll('.cancel-event-btn').forEach((btn) => {
        btn.addEventListener('click', closeDialog, pageListenerOptions);
    });
    eventDeleteBtn?.addEventListener('click', deleteEvent, pageListenerOptions);
    eventForm?.addEventListener('submit', saveEvent, pageListenerOptions);
    eventAllDayInput?.addEventListener('change', applyAllDayTimes, pageListenerOptions);
    eventColorPicker?.addEventListener('input', () => chooseEventColor(eventColorPicker.value), pageListenerOptions);
    eventColorReset?.addEventListener('click', () => chooseEventColor(''), pageListenerOptions);
    eventColorInput?.addEventListener('input', syncEventColor, pageListenerOptions);
    eventColorInput?.addEventListener('change', syncEventColor, pageListenerOptions);

    dialogOverlay?.addEventListener('click', (e) => {
        if (e.target === dialogOverlay) closeDialog();
    }, pageListenerOptions);

    document.addEventListener('keydown', (e) => {
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
        renderCurrentView();
    }, pageListenerOptions);
    retryButton.addEventListener('click', fetchEvents, pageListenerOptions);
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
    syncEventColor();
    renderCurrentView();
    fetchEvents();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCalendarPage);
} else {
    initCalendarPage();
}

document.addEventListener('ancore:content-loaded', initCalendarPage);
