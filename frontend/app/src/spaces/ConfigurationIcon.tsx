import { useRef, useState, type KeyboardEvent } from 'react';
import { type Field } from '../forms/FormDialog';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';

const scalar = (value: Field['value']) => (Array.isArray(value) ? value[0] || '' : value || '');
const normalize = (value: string) =>
  value
    .toLocaleLowerCase('pl')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/ł/g, 'l')
    .trim();

export default function ConfigurationIcon({
  field,
  defaultIcon,
  subject = 'typu',
}: {
  field: Field;
  defaultIcon: string;
  subject?: 'typu' | 'etapu' | 'kategorii' | 'grupy';
}) {
  const defaultLabel = `Domyślna dla ${subject}`;
  const [value, setValue] = useState(() => scalar(field.value));
  const [query, setQuery] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const grid = useRef<HTMLDivElement>(null);
  const selected = field.choices?.find((choice) => choice.value === value);
  const icon = value ? selected?.icon || defaultIcon : defaultIcon;
  const label = selected?.label || defaultLabel;
  const terms = normalize(query).split(/\s+/).filter(Boolean);
  const choices = (field.choices || []).filter(
    (choice) =>
      choice.value &&
      terms.every((term) => normalize(`${choice.label} ${choice.value}`).includes(term)),
  );
  function gridKeys(event: KeyboardEvent<HTMLDivElement>) {
    const buttons = [
      ...event.currentTarget.querySelectorAll<HTMLButtonElement>('[data-type-icon]'),
    ];
    const index = buttons.indexOf(event.target as HTMLButtonElement);
    if (
      index < 0 ||
      !['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)
    )
      return;
    event.preventDefault();
    event.stopPropagation();
    const next =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? buttons.length - 1
          : Math.max(
              0,
              Math.min(
                buttons.length - 1,
                index +
                  ({ ArrowRight: 1, ArrowLeft: -1, ArrowDown: 8, ArrowUp: -8 }[event.key] || 0),
              ),
            );
    buttons[next]?.focus();
    buttons[next]?.scrollIntoView({ block: 'nearest' });
  }
  function choose(next: string, close: () => void) {
    if (field.disabled) return;
    if (next !== value) {
      setValue(next);
      input.current!.value = next;
      input.current!.dispatchEvent(new Event('input', { bubbles: true }));
      input.current!.dispatchEvent(new Event('change', { bubbles: true }));
    }
    close();
  }
  return (
    <div className="profile-photo-control work-type-icon-control">
      <input
        ref={input}
        type="hidden"
        name={field.name}
        value={value}
        disabled={field.disabled}
        readOnly
      />
      <Dropdown
        label={`Zmień ikonę ${subject}: ${label}`}
        className="emoji-picker work-type-icon-picker"
        menuClass="emoji-picker-menu work-type-icon-menu"
        role="dialog"
        triggerClassName="work-type-icon-trigger"
        searchable={false}
        disabled={field.disabled}
        onOpen={() => {
          setQuery('');
          requestAnimationFrame(() => search.current?.focus());
        }}
        triggerProps={{
          id: field.id,
          'aria-invalid': !!field.errors.length,
          'aria-describedby': field.errors.length ? `${field.id}_error` : undefined,
        }}
        trigger={
          <>
            <span
              className="tasks-issue-type profile-page-avatar work-type-icon-preview"
              aria-hidden="true"
            >
              <Icon name={icon} />
            </span>
            <span className="profile-photo-button">Zmień</span>
          </>
        }
      >
        {(close) => (
          <>
            <div className="ancore-custom-select__search">
              <Icon name="search" />
              <input
                ref={search}
                type="search"
                className="ancore-custom-select__search-input"
                aria-label="Szukaj ikon"
                placeholder="Szukaj ikon…"
                value={query}
                onChange={(event) => event.stopPropagation()}
                onInputCapture={(event) => {
                  event.stopPropagation();
                  setQuery(event.currentTarget.value);
                }}
                onKeyDown={(event) => {
                  if (event.key === 'ArrowDown' || event.key === 'Enter') {
                    event.preventDefault();
                    event.stopPropagation();
                    const first =
                      grid.current?.querySelector<HTMLButtonElement>('[data-type-icon]');
                    if (event.key === 'Enter') first?.click();
                    else first?.focus();
                  }
                }}
              />
            </div>
            <button
              type="button"
              aria-pressed={!value}
              className="tasks-project-menu-button emoji-picker-default"
              onClick={() => choose('', close)}
            >
              <span className="tasks-issue-type" aria-hidden="true">
                <Icon name={defaultIcon} />
              </span>
              <span>{defaultLabel}</span>
              {!value ? <Icon name="check" /> : null}
            </button>
            <div className="emoji-picker-caption" role="status">
              {terms.length
                ? 'Wyniki wyszukiwania'
                : subject === 'etapu'
                  ? 'Ikony statusów'
                  : 'Wszystkie ikony'}{' '}
              · {choices.length}
            </div>
            <div className="emoji-picker-results">
              {choices.length ? (
                <div ref={grid} className="emoji-picker-grid" onKeyDown={gridKeys}>
                  {choices.map((choice, index) => (
                    <button
                      type="button"
                      key={choice.value}
                      data-type-icon={choice.value}
                      tabIndex={index === 0 ? 0 : -1}
                      aria-label={choice.label}
                      title={choice.label}
                      aria-pressed={value === choice.value}
                      onClick={() => choose(choice.value, close)}
                    >
                      <span className="tasks-issue-type" aria-hidden="true">
                        <Icon name={choice.icon || defaultIcon} />
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <p className="emoji-picker-empty">Brak pasujących ikon.</p>
              )}
            </div>
            <div className="emoji-picker-footer">
              <span className="tasks-issue-type" aria-hidden="true">
                <Icon name={icon} />
              </span>
              <span>{label}</span>
            </div>
          </>
        )}
      </Dropdown>
      {field.errors.length ? (
        <div className="tasks-modal__errors" role="alert" id={`${field.id}_error`}>
          {field.errors.map((message, index) => (
            <p key={index}>{message}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
