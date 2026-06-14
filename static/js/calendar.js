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
    const DAY_VIEW_HOURS = { start: 6, end: 22 };

    let anchorDate = startOfDay(new Date());
    let currentView = 'month';
    let events = [];
    let fetchToken = 0;

    const periodLabel = document.getElementById('cal-period-label');
    const eventsSubtitle = document.getElementById('cal-events-subtitle');
    const eventsList = document.getElementById('calendar-events-list');
    const weekdaysHeader = document.getElementById('cal-weekdays-header');
    const viewContainers = {
        month: document.getElementById('calendar-view-month'),
        week: document.getElementById('calendar-view-week'),
        day: document.getElementById('calendar-view-day'),
        year: document.getElementById('calendar-view-year'),
    };
    const monthDaysEl = document.getElementById('calendar-days-month');
    const weekHeaderEl = document.getElementById('calendar-week-header');
    const weekColumnsEl = document.getElementById('calendar-week-columns');
    const dayScheduleEl = document.getElementById('calendar-day-schedule');
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
        const gridEnd = addDays(gridStart, 41);
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

    function normalizeAnchorForView(view) {
        const y = anchorDate.getFullYear();
        const m = anchorDate.getMonth();
        const d = anchorDate.getDate();
        switch (view) {
            case 'year':
                anchorDate = new Date(y, 0, 1);
                break;
            case 'month':
                anchorDate = new Date(y, m, 1);
                break;
            case 'week':
            case 'day':
                anchorDate = new Date(y, m, d);
                break;
            default:
                break;
        }
    }

    function eventOccursOnDay(event, day) {
        const start = new Date(event.start);
        const end = new Date(event.end);
        return start <= endOfDay(day) && end >= startOfDay(day);
    }

    function eventInHourSlot(event, day, hour) {
        if (event.all_day) return false;
        const start = new Date(event.start);
        const end = new Date(event.end);
        const slotStart = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour, 0, 0, 0);
        const slotEnd = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hour + 1, 0, 0, 0);
        return start < slotEnd && end > slotStart;
    }

    function eventsOnDay(day) {
        return events
            .filter((event) => eventOccursOnDay(event, day))
            .sort((a, b) => new Date(a.start) - new Date(b.start));
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
        return `${date.getDate()} ${MONTH_NAMES[date.getMonth()]}`;
    }

    function updatePeriodLabel() {
        const y = anchorDate.getFullYear();
        const m = anchorDate.getMonth();

        switch (currentView) {
            case 'year':
                periodLabel.textContent = String(y);
                break;
            case 'month':
                periodLabel.textContent = `${MONTH_NAMES[m]} ${y}`;
                break;
            case 'week': {
                const ws = startOfWeek(anchorDate);
                const we = endOfWeek(anchorDate);
                const labelYear = we.getFullYear();
                periodLabel.textContent = ws.getMonth() === we.getMonth()
                    ? `${ws.getDate()}–${we.getDate()} ${MONTH_NAMES[ws.getMonth()]} ${labelYear}`
                    : `${ws.getDate()} ${MONTH_NAMES[ws.getMonth()]} – ${we.getDate()} ${MONTH_NAMES[we.getMonth()]} ${labelYear}`;
                break;
            }
            case 'day':
                periodLabel.textContent = `${DAY_NAMES[anchorDate.getDay()]}, ${anchorDate.getDate()} ${MONTH_NAMES[m]} ${y}`;
                break;
            default:
                break;
        }
    }

    function updateEventsSubtitle() {
        const { start, end } = getFetchRange();
        const today = startOfDay(new Date());
        const periodLabels = {
            year: 'w tym roku',
            month: 'w tym miesiącu',
            week: 'w tym tygodniu',
            day: isSameDay(anchorDate, today) ? 'dzisiaj' : 'tego dnia',
        };
        const label = periodLabels[currentView] || '';
        if (currentView === 'day') {
            eventsSubtitle.textContent = `${label} · ${formatShortDate(anchorDate)}`;
        } else {
            eventsSubtitle.textContent = `${label} · ${formatShortDate(start)} – ${formatShortDate(end)}`;
        }
    }

    function createEventButton(event, showTime) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `calendar-event calendar-event--${event.color}`;
        const timePrefix = showTime && !event.all_day
            ? `${formatEventTime(event).split(' – ')[0]} `
            : '';
        btn.textContent = `${timePrefix}${event.title}`;
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openDialog('edit', null, event);
        });
        return btn;
    }

    function appendEventsToCell(container, dayEvents, max) {
        const limit = max ?? MAX_EVENTS_PER_CELL;
        dayEvents.slice(0, limit).forEach((event) => {
            container.appendChild(createEventButton(event, true));
        });
        if (dayEvents.length > limit) {
            const more = document.createElement('span');
            more.className = 'calendar-event-more';
            more.textContent = `+${dayEvents.length - limit} więcej`;
            container.appendChild(more);
        }
    }

    function renderMonthView() {
        const today = startOfDay(new Date());
        const year = anchorDate.getFullYear();
        const monthIndex = anchorDate.getMonth();
        const { gridStart } = getMonthGridBounds(year, monthIndex);

        monthDaysEl.innerHTML = '';

        for (let i = 0; i < 42; i += 1) {
            const dayDate = addDays(gridStart, i);

            const cell = document.createElement('div');
            cell.className = 'calendar-day';
            cell.setAttribute('role', 'gridcell');

            if (dayDate.getMonth() !== monthIndex) cell.classList.add('calendar-day--other');
            if (isSameDay(dayDate, today)) cell.classList.add('calendar-day--today');

            const dayNumber = document.createElement('span');
            dayNumber.className = 'calendar-day-number';
            dayNumber.textContent = dayDate.getDate();
            cell.appendChild(dayNumber);

            const eventsWrap = document.createElement('div');
            eventsWrap.className = 'calendar-day-events';
            appendEventsToCell(eventsWrap, eventsOnDay(dayDate));
            cell.appendChild(eventsWrap);

            cell.addEventListener('click', () => {
                anchorDate = cloneDate(dayDate);
                setView('day');
            });
            monthDaysEl.appendChild(cell);
        }
    }

    function renderWeekView() {
        const today = startOfDay(new Date());
        const weekStart = startOfWeek(anchorDate);

        weekHeaderEl.innerHTML = '';
        weekColumnsEl.innerHTML = '';

        for (let i = 0; i < 7; i += 1) {
            const dayDate = addDays(weekStart, i);
            const isWeekend = i >= 5;

            const headerCell = document.createElement('button');
            headerCell.type = 'button';
            headerCell.className = `calendar-week-day-head${isWeekend ? ' calendar-weekend' : ''}`;
            if (isSameDay(dayDate, today)) headerCell.classList.add('calendar-week-day-head--today');
            headerCell.innerHTML = `<span class="calendar-week-day-name">${WEEKDAY_SHORT[i]}</span><span class="calendar-week-day-num">${dayDate.getDate()}</span>`;
            headerCell.addEventListener('click', () => {
                anchorDate = cloneDate(dayDate);
                setView('day');
            });
            weekHeaderEl.appendChild(headerCell);

            const col = document.createElement('div');
            col.className = 'calendar-week-col';
            if (isSameDay(dayDate, today)) col.classList.add('calendar-week-col--today');

            const eventsWrap = document.createElement('div');
            eventsWrap.className = 'calendar-week-col-events';
            appendEventsToCell(eventsWrap, eventsOnDay(dayDate), 12);
            col.appendChild(eventsWrap);
            col.addEventListener('click', () => openDialog('create', dayDate, null));
            weekColumnsEl.appendChild(col);
        }
    }

    function renderDayView() {
        const today = startOfDay(new Date());
        const day = startOfDay(anchorDate);

        dayScheduleEl.innerHTML = '';
        dayScheduleEl.classList.toggle('calendar-day-schedule--today', isSameDay(day, today));

        const dayEvents = eventsOnDay(day);
        const allDayEvents = dayEvents.filter((e) => e.all_day);
        const timedEvents = dayEvents.filter((e) => !e.all_day);

        const allDayRow = document.createElement('div');
        allDayRow.className = 'calendar-day-allday';
        allDayRow.innerHTML = '<span class="calendar-day-slot-label">Cały dzień</span>';
        const allDayWrap = document.createElement('div');
        allDayWrap.className = 'calendar-day-allday-events';
        if (allDayEvents.length) {
            allDayEvents.forEach((event) => allDayWrap.appendChild(createEventButton(event, true)));
        } else {
            allDayWrap.innerHTML = '<span class="calendar-day-empty-slot">Brak wydarzeń</span>';
        }
        allDayRow.appendChild(allDayWrap);
        dayScheduleEl.appendChild(allDayRow);

        for (let h = DAY_VIEW_HOURS.start; h <= DAY_VIEW_HOURS.end; h += 1) {
            const row = document.createElement('div');
            row.className = 'calendar-day-slot';
            row.innerHTML = `<span class="calendar-day-slot-label">${pad(h)}:00</span>`;
            const slotBody = document.createElement('div');
            slotBody.className = 'calendar-day-slot-body';

            const hourEvents = timedEvents.filter((e) => eventInHourSlot(e, day, h));
            if (hourEvents.length) {
                hourEvents.forEach((event) => slotBody.appendChild(createEventButton(event, true)));
            }

            slotBody.addEventListener('click', (e) => {
                if (e.target.closest('.calendar-event')) return;
                const preset = new Date(day);
                preset.setHours(h, 0, 0, 0);
                openDialog('create', preset, null);
            });
            row.appendChild(slotBody);
            dayScheduleEl.appendChild(row);
        }
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
                anchorDate = new Date(year, m, 1);
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
                        anchorDate = cloneDate(dayDate);
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
        const sorted = [...events].sort((a, b) => new Date(a.start) - new Date(b.start));

        if (!sorted.length) {
            const empty = document.createElement('li');
            empty.className = 'calendar-events-empty';
            empty.textContent = 'Brak wydarzeń w wybranym okresie.';
            eventsList.appendChild(empty);
            return;
        }

        sorted.forEach((event) => {
            const li = document.createElement('button');
            li.type = 'button';
            li.className = `calendar-list-item calendar-list-item--${event.color}`;
            const start = new Date(event.start);
            li.innerHTML = `
                <span class="calendar-list-time">${formatEventTime(event)}</span>
                <div class="calendar-list-body">
                    <span class="calendar-list-title">${event.title}</span>
                    <span class="calendar-list-date">${formatShortDate(start)}${event.all_day ? '' : ` · ${pad(start.getHours())}:${pad(start.getMinutes())}`}</span>
                </div>
            `;
            li.addEventListener('click', () => openDialog('edit', null, event));
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
        currentView = view;
        normalizeAnchorForView(view);

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
        const { start, end } = getFetchRange();
        const params = new URLSearchParams({
            start: toLocalISO(start),
            end: toLocalISO(end),
        });

        try {
            const response = await fetch(`${urls.events}?${params.toString()}`);
            const data = await response.json();
            if (token !== fetchToken) return;
            if (data.status === 'success') {
                events = data.events;
                renderCurrentView();
            }
        } catch (err) {
            console.error('Nie udało się pobrać wydarzeń:', err);
        }
    }

    function navigate(delta) {
        const y = anchorDate.getFullYear();
        const m = anchorDate.getMonth();
        const d = anchorDate.getDate();

        switch (currentView) {
            case 'year':
                anchorDate = new Date(y + delta, 0, 1);
                break;
            case 'month':
                anchorDate = new Date(y, m + delta, 1);
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

        renderCurrentView();
        fetchEvents();
    }

    function goToToday() {
        anchorDate = startOfDay(new Date());
        normalizeAnchorForView(currentView);
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
        clearFormError();
        eventForm.reset();

        if (mode === 'create') {
            eventDialogTitle.textContent = 'Nowe wydarzenie';
            eventDeleteBtn.classList.add('u-hidden');
            eventIdInput.value = '';

            const base = presetDate ? startOfDay(presetDate) : startOfDay(anchorDate);
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
        dialogOverlay.classList.remove('active');
        dialogOverlay.setAttribute('aria-hidden', 'true');
        clearFormError();
    }

    function applyAllDayTimes() {
        if (!eventAllDayInput.checked) return;
        const start = parseLocalInput(eventStartInput.value);
        const end = parseLocalInput(eventEndInput.value);
        start.setHours(0, 0, 0, 0);
        end.setHours(23, 59, 0, 0);
        eventStartInput.value = toLocalInputValue(start);
        eventEndInput.value = toLocalInputValue(end);
    }

    async function saveEvent(e) {
        e.preventDefault();
        clearFormError();
        applyAllDayTimes();

        const formData = new FormData();
        formData.append('title', eventTitleInput.value.trim());
        formData.append('description', eventDescInput.value.trim());
        formData.append('start', eventStartInput.value);
        formData.append('end', eventEndInput.value);
        formData.append('all_day', eventAllDayInput.checked ? 'on' : '');
        formData.append('color', eventColorInput.value);

        const eventId = eventIdInput.value;
        const url = eventId ? apiUrl('update', eventId) : urls.create;

        const response = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrfToken },
            body: formData,
        });
        const data = await response.json();

        if (data.status === 'success') {
            closeDialog();
            fetchEvents();
            return;
        }

        if (data.errors) {
            const firstError = Object.values(data.errors).flat()[0];
            showFormError(firstError || 'Nie udało się zapisać wydarzenia.');
        } else {
            showFormError(data.message || 'Nie udało się zapisać wydarzenia.');
        }
    }

    async function deleteEvent() {
        const eventId = eventIdInput.value;
        if (!eventId) return;

        showConfirmModal({
            title: 'Usuń wydarzenie',
            message: 'Czy na pewno chcesz usunąć to wydarzenie?',
            confirmText: 'Usuń',
            confirmClass: 'btn-danger',
            onConfirm: async () => {
                const response = await fetch(apiUrl('delete', eventId), {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken },
                });
                const data = await response.json();
                if (data.status === 'success') {
                    closeDialog();
                    fetchEvents();
                }
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

        if (e.key === 'Escape' && dialogOverlay?.classList.contains('active')) {
            closeDialog();
        }
    }, pageListenerOptions);

    syncEventColorSelect();
    normalizeAnchorForView(currentView);
    renderCurrentView();
    fetchEvents();
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCalendarPage);
} else {
    initCalendarPage();
}

document.addEventListener('ancore:content-loaded', initCalendarPage);
