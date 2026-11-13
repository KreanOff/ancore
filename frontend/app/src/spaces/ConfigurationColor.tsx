import { useState, type CSSProperties } from 'react';
import type { Field } from '../forms/FormDialog';
import { ColorControl } from '../shared/ColorControl';
import { FieldLabel } from '../shared/FieldLabel';
import { configurationBadgeClass, configurationColor } from './configuration-appearance';

export default function ConfigurationColor({ field }: { field: Field }) {
  const [value, setValue] = useState(String(field.value || ''));
  const color = configurationColor({ ...field, value });
  const describedBy = `${field.id}_help${field.errors.length ? ` ${field.id}_error` : ''}`;
  return (
    <div className="documents-field tasks-form-field app-form-wide">
      <FieldLabel
        htmlFor={field.id}
        label={field.label}
        helpText={field.help_text}
        helpId={`${field.id}_help`}
      />
      <ColorControl
        id={field.id}
        name={field.name}
        value={value}
        color={color}
        label="Wybierz kolor nazwy"
        placeholder={field.attrs.placeholder}
        pattern={field.attrs.pattern}
        disabled={field.disabled}
        invalid={!!field.errors.length}
        describedBy={describedBy}
        onChange={setValue}
      >
        <span className={configurationBadgeClass} style={{ '--tag-color': color } as CSSProperties}>
          Podgląd
        </span>
      </ColorControl>
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
