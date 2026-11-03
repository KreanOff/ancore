import { useRef, useState, type CSSProperties } from 'react';
import type { Field } from '../forms/FormDialog';
import { FieldLabel } from '../shared/FieldLabel';
import { configurationBadgeClass, configurationColor } from './configuration-appearance';

export default function ConfigurationColor({ field }: { field: Field }) {
  const [value, setValue] = useState(String(field.value || ''));
  const input = useRef<HTMLInputElement>(null);
  const color = configurationColor({ ...field, value });
  const describedBy = `${field.id}_help${field.errors.length ? ` ${field.id}_error` : ''}`;
  function choose(next: string) {
    setValue(next);
    input.current!.value = next;
    input.current!.dispatchEvent(new Event('input', { bubbles: true }));
  }
  return (
    <div className="documents-field tasks-form-field app-form-wide">
      <FieldLabel
        htmlFor={field.id}
        label={field.label}
        helpText={field.help_text}
        helpId={`${field.id}_help`}
      />
      <div className="documents-color-control work-configuration-color">
        <input
          type="color"
          className="documents-color-input"
          aria-label="Wybierz kolor nazwy"
          value={color}
          disabled={field.disabled}
          onChange={(event) => choose(event.target.value)}
        />
        <input
          ref={input}
          id={field.id}
          name={field.name}
          className="form-input"
          value={value}
          placeholder={field.attrs.placeholder}
          maxLength={7}
          pattern={field.attrs.pattern}
          disabled={field.disabled}
          aria-invalid={!!field.errors.length}
          aria-describedby={describedBy}
          onChange={(event) => setValue(event.target.value)}
        />
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          disabled={field.disabled}
          onClick={() => choose('')}
        >
          Domyślny
        </button>
        <span className={configurationBadgeClass} style={{ '--tag-color': color } as CSSProperties}>
          Podgląd
        </span>
      </div>
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
