import { type FormEvent, useEffect, useRef, useState } from 'react';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { Modal } from '../shared/Modal';
import { PageError, pageRequest } from '../shared/page';
import { errorMessage } from '../shared/api';
import {
  colors,
  eventDate,
  eventDateValue,
  eventInput,
  localInput,
  type CalendarEvent,
} from './dates';

export function EventEditor({
  event,
  date,
  allDay: initialAllDay = false,
  api,
  urls,
  csrfToken,
  onClose,
  onSaved,
  readOnly = false,
}: {
  event: CalendarEvent | null;
  date: Date;
  allDay?: boolean;
  api: string;
  urls: { create: string; update: string; delete: string };
  csrfToken: string;
  onClose: () => void;
  onSaved: (message: string) => void;
  readOnly?: boolean;
}) {
  const form = useRef<HTMLFormElement>(null);
  const errorSummary = useRef<HTMLParagraphElement>(null);
  const [dirty, setDirty] = useState(false),
    [pending, setPending] = useState(false),
    [error, setError] = useState('');
  const [color, setColor] = useState(event?.color || 'red');
  const [errors, setErrors] = useState<Record<string, string[]>>({});
  const controller = useRef(new AbortController());
  const sending = useRef(false);
  useEffect(() => () => controller.current.abort(), []);
  useEffect(() => {
    if (!error || pending) return;
    const invalid = form.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
    (invalid || errorSummary.current)?.focus();
  }, [error, errors, pending]);
  const start = new Date(date);
  const end = new Date(start);
  end.setHours(end.getHours() + 1);
  if (initialAllDay) {
    start.setHours(0, 0, 0, 0);
    end.setHours(23, 59, 0, 0);
  }
  function allDay(checked: boolean) {
    const element = form.current!;
    for (const [name, ending] of [
      ['start', false],
      ['end', true],
    ] as const) {
      const input = element.elements.namedItem(name) as HTMLInputElement;
      if (!input.value) continue;
      input.value =
        input.value.slice(0, 10) +
        (checked ? (ending ? 'T23:59' : 'T00:00') : ending ? 'T10:00' : 'T09:00');
    }
    setDirty(true);
  }
  async function save(e: FormEvent) {
    e.preventDefault();
    if (sending.current) return;
    const data = new FormData(form.current!);
    data.set('color', color);
    sending.current = true;
    setPending(true);
    setError('');
    setErrors({});
    try {
      for (const name of ['start', 'end'] as const)
        data.set(
          name,
          eventDateValue(
            String(data.get(name) || ''),
            !!data.get('all_day'),
            event ? { event, name } : undefined,
          ),
        );
      await pageRequest(
        api,
        event ? urls.update.replace('__ID__', String(event.id)) : urls.create,
        csrfToken,
        controller.current.signal,
        data,
      );
      onSaved('Wydarzenie zapisane.');
    } catch (exception) {
      if (controller.current.signal.aborted) return;
      if (exception instanceof PageError && exception.data.errors)
        setErrors(exception.data.errors as Record<string, string[]>);
      setError(errorMessage(exception));
    } finally {
      sending.current = false;
      setPending(false);
    }
  }
  function remove() {
    if (!event || sending.current) return;
    window.showConfirmModal({
      title: 'Usuń wydarzenie',
      message: window.escapeHtmlForModal(`Usunąć wydarzenie „${event.title}”?`),
      confirmText: 'Usuń',
      cancelText: 'Anuluj',
      onConfirm: async () => {
        if (controller.current.signal.aborted || sending.current) return;
        sending.current = true;
        setPending(true);
        setError('');
        try {
          await pageRequest(
            api,
            urls.delete.replace('__ID__', String(event.id)),
            csrfToken,
            controller.current.signal,
            new FormData(),
          );
          onSaved('Wydarzenie usunięte.');
        } catch (exception) {
          if (!controller.current.signal.aborted) setError(errorMessage(exception));
        } finally {
          sending.current = false;
          setPending(false);
        }
      },
    });
  }
  const fieldErrors = (name: string) =>
    errors[name]?.length ? (
      <p id={`react-event-${name}-error`} className="calendar-form-error" role="alert">
        {errors[name].join(' ')}
      </p>
    ) : null;
  if (readOnly)
    return (
      <Modal title="Wydarzenie" onClose={onClose}>
        <div className="tasks-modal__body">
          <h3>{event?.title}</h3>
          <p>{event?.description}</p>
          <p>{event ? eventDate(event).toLocaleString('pl-PL') : ''}</p>
          <p>Gość ma dostęp tylko do odczytu.</p>
        </div>
      </Modal>
    );
  return (
    <Modal
      title={event ? 'Edytuj wydarzenie' : 'Nowe wydarzenie'}
      className="calendar-modal"
      dirty={dirty}
      pending={pending}
      onClose={onClose}
    >
      <form
        ref={form}
        id="react-event-form"
        className="tasks-modal__form calendar-dialog-form"
        onSubmit={save}
        onChange={() => setDirty(true)}
        aria-busy={pending}
      >
        <div className="tasks-modal__body calendar-dialog-body app-form-layout">
          {error ? (
            <p
              ref={errorSummary}
              tabIndex={-1}
              role="alert"
              className="calendar-form-error app-form-wide"
            >
              {error}
              {errors.__all__?.join(' ')}
            </p>
          ) : null}
          <div className="app-form-heading">
            <div className="calendar-dialog-field app-form-field">
              <label className="form-label" htmlFor="react-event-title">
                Tytuł
              </label>
              <input
                id="react-event-title"
                name="title"
                className="tasks-inline-input"
                defaultValue={event?.title || ''}
                required
                maxLength={255}
                placeholder="Tytuł wydarzenia"
                disabled={pending}
                aria-invalid={!!errors.title?.length}
                aria-describedby={errors.title?.length ? 'react-event-title-error' : undefined}
              />
              {fieldErrors('title')}
            </div>
          </div>
          <div className="calendar-dialog-field app-form-field app-form-description">
            <label className="form-label" htmlFor="react-event-description">
              Opis
            </label>
            <textarea
              id="react-event-description"
              name="description"
              className="tasks-inline-input calendar-dialog-desc"
              defaultValue={event?.description || ''}
              disabled={pending}
              placeholder="Opis (opcjonalnie)"
              aria-invalid={!!errors.description?.length}
              aria-describedby={
                errors.description?.length ? 'react-event-description-error' : undefined
              }
            />
            {fieldErrors('description')}
          </div>
          {(
            [
              ['start', 'Rozpoczęcie', event?.start || start],
              ['end', 'Zakończenie', event?.end || end],
            ] as const
          ).map(([name, label, value]) => (
            <div className="calendar-dialog-field app-form-field" key={name}>
              <label className="form-label" htmlFor={`react-event-${name}`}>
                {label}
              </label>
              <input
                type="datetime-local"
                id={`react-event-${name}`}
                name={name}
                className="tasks-inline-input"
                defaultValue={event ? eventInput(event, name) : localInput(new Date(value))}
                required
                disabled={pending}
                aria-invalid={!!errors[name]?.length}
                aria-describedby={errors[name]?.length ? `react-event-${name}-error` : undefined}
              />
              {fieldErrors(name)}
            </div>
          ))}
          <div className="calendar-dialog-field calendar-checkbox-field app-form-field">
            <label className="form-label form-label--checkbox">
              <input
                type="checkbox"
                name="all_day"
                className="form-checkbox"
                defaultChecked={event?.all_day || initialAllDay}
                disabled={pending}
                aria-invalid={!!errors.all_day?.length}
                aria-describedby={errors.all_day?.length ? 'react-event-all_day-error' : undefined}
                onChange={(e) => allDay(e.target.checked)}
              />
              Cały dzień
            </label>
            {fieldErrors('all_day')}
          </div>
          <div className="calendar-dialog-field app-form-field">
            <span className="form-label">Kolor</span>
            <Dropdown
              label="Kolor wydarzenia"
              disabled={pending}
              triggerProps={{
                'aria-invalid': !!errors.color?.length,
                'aria-describedby': errors.color?.length ? 'react-event-color-error' : undefined,
              }}
              trigger={
                <>
                  <span className={`calendar-color-dot calendar-color-dot--${color}`} />
                  <span>{colors.find((item) => item[0] === color)?.[1]}</span>
                  <Icon name="chevron-down" />
                </>
              }
            >
              {(close) =>
                colors.map(([value, label]) => (
                  <button
                    type="button"
                    key={value}
                    role="menuitemradio"
                    aria-checked={color === value}
                    disabled={pending}
                    onClick={() => {
                      setColor(value);
                      setDirty(true);
                      close();
                    }}
                  >
                    <span className={`calendar-color-dot calendar-color-dot--${value}`} />
                    <span>{label}</span>
                  </button>
                ))
              }
            </Dropdown>
            {fieldErrors('color')}
          </div>
        </div>
        <footer className="tasks-modal__footer calendar-dialog-footer">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={pending}
            onClick={() =>
              form.current?.closest('.tasks-modal') &&
              window.AncoreTaskModals?.close(form.current.closest('.tasks-modal') as HTMLElement)
            }
          >
            Anuluj
          </button>
          {event ? (
            <button type="button" className="btn btn-danger" disabled={pending} onClick={remove}>
              Usuń wydarzenie
            </button>
          ) : null}
          <button type="submit" className="tasks-modal__submit" disabled={pending}>
            {pending ? 'Zapisywanie…' : 'Zapisz'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
