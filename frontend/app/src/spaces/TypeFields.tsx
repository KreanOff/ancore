import { useRef, useState, type KeyboardEvent } from 'react';
import { FieldControl, type Field, type FormSchema } from '../forms/FormDialog';
import { Dropdown } from '../shared/Dropdown';
import { Icon } from '../shared/Icon';
import { configurationFieldName } from './configuration-form';

const scalar = (value: Field['value']) => (Array.isArray(value) ? value[0] || '' : value || '');
const normalize = (value: string) =>
  value
    .toLocaleLowerCase('pl')
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .replace(/ł/g, 'l')
    .trim();

function TypeIcon({ field, defaultIcon }: { field: Field; defaultIcon: string }) {
  const [value, setValue] = useState(() => scalar(field.value));
  const [query, setQuery] = useState('');
  const input = useRef<HTMLInputElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const grid = useRef<HTMLDivElement>(null);
  const selected = field.choices?.find((choice) => choice.value === value);
  const icon = value ? selected?.icon || 'shapes' : defaultIcon;
  const label = selected?.label || 'Domyślna dla typu';
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
        label={`Zmień ikonę typu: ${label}`}
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
              <span>Domyślna dla typu</span>
              {!value ? <Icon name="check" /> : null}
            </button>
            <div className="emoji-picker-caption" role="status">
              {terms.length ? 'Wyniki wyszukiwania' : 'Wszystkie ikony'} · {choices.length}
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
                        <Icon name={choice.icon || 'shapes'} />
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

export default function TypeFields({
  schema,
  iconDefaults,
}: {
  schema: FormSchema;
  iconDefaults?: Record<string, string>;
}) {
  const fields = Object.fromEntries(
    schema.fields.map((field) => [configurationFieldName(field), field]),
  );
  const [key, setKey] = useState(() => scalar(fields.key?.value));
  const defaultIcon =
    iconDefaults?.[key] ||
    (!iconDefaults && key === scalar(fields.key?.value)
      ? fields.icon?.choices?.find((choice) => choice.value === '')?.icon
      : undefined) ||
    'shapes';
  return (
    <>
      {fields.icon ? <TypeIcon field={fields.icon} defaultIcon={defaultIcon} /> : null}
      <div
        className="space-settings-fields"
        onInput={(event) => {
          const target = event.target;
          if (target instanceof HTMLInputElement && target.name === fields.key?.name)
            setKey(target.value);
        }}
      >
        <div className="app-form-layout">
          {fields.label ? (
            <div className="app-form-heading">
              <FieldControl field={fields.label} />
            </div>
          ) : null}
          {fields.description ? (
            <div className="app-form-description">
              <FieldControl field={fields.description} />
            </div>
          ) : null}
          {fields.key ? <FieldControl field={fields.key} /> : null}
          {schema.fields
            .filter((field) => field.hidden)
            .map((field) => (
              <FieldControl field={field} key={field.name} />
            ))}
        </div>
      </div>
    </>
  );
}
